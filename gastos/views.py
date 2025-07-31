from django.shortcuts import render, redirect, get_object_or_404
from django.db import models, transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Movimiento
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings
import logging
from .forms import MovimientoForm, FiltroMovimientosForm
from django.db.models.functions import TruncMonth
from collections import defaultdict
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa 

# Configurar límites según el ambiente
if settings.DEBUG:
    # LÍMITES RELAJADOS PARA DESARROLLO
    LIMITE_MOVIMIENTOS_DIA = 100  # Más permisivo para testing
    LIMITE_ARCHIVOS_HORA = 50     # Más permisivo para testing
    LIMITE_REGISTROS_EXPORT = 5000  # Más registros para testing
    
    logger = logging.getLogger('finanzas')
    logger.info("🔧 Límites de desarrollo aplicados")
    
else:
    # LÍMITES ESTRICTOS PARA PRODUCCIÓN
    LIMITE_MOVIMIENTOS_DIA = 50
    LIMITE_ARCHIVOS_HORA = 10
    LIMITE_REGISTROS_EXPORT = 1000
    
    logger = logging.getLogger('finanzas.security')
    logger.info("🚀 Límites de producción aplicados")


# Configurar logging para seguridad
logger = logging.getLogger(__name__)

@login_required
def balance_view(request):
    """
    Vista del balance general con cache y optimizaciones
    """
    try:
        # Optimizar consultas con select_related si hay relaciones
        movimientos_query = Movimiento.objects.filter(usuario=request.user)

        # Agregar agregaciones en una sola consulta
        resumen = movimientos_query.aggregate(
            total_ingresos=Sum('monto', filter=Q(tipo='ingreso')),
            total_gastos=Sum('monto', filter=Q(tipo='gasto')),
            count_movimientos=models.Count('id')
        )

        ingresos = resumen['total_ingresos'] or 0
        gastos = resumen['total_gastos'] or 0
        balance = ingresos - gastos

        # Obtener últimos movimientos de forma eficiente
        ultimos_movimientos = movimientos_query.order_by('-fecha', '-creado_en')[:10]

        contexto = {
            'ingresos': ingresos,
            'gastos': gastos,
            'balance': balance,
            'movimientos': ultimos_movimientos,
            'total_movimientos': resumen['count_movimientos'],
        }

        return render(request,'gastos/balance.html', contexto)
    
    except Exception as e:
        logger.error(f"Error en balance_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar el balance. Intenta nuevamente.")
        return render(request, 'gastos/balance.html', {
            'ingresos': 0, 'gastos': 0, 'balance': 0, 'movimientos': []
        })

@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def crear_movimiento_view(request):
    """
    Vista para crear movimientos con validaciones mejoradas
    """
    if request.method == 'POST':
        form = MovimientoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Crear movimiento
                movimiento = form.save(commit=False)
                movimiento.usuario = request.user
                movimiento.save()
                
                messages.success(request, 'Movimiento creado exitosamente')
                return redirect('balance')
                
            except Exception as e:
                messages.error(request, f'Error al crear movimiento: {e}')
                return render(request, 'crear_movimiento.html', {'form': form})
        else:
            messages.error(request, 'Por favor corrige los errores del formulario')
    else:
        form = MovimientoForm()
    
    # IMPORTANTE: Siempre retornar una respuesta
    context = {
        'form': form,
        'titulo': 'Crear Movimiento'
    }
    return render(request, 'crear_movimiento.html', context)

@login_required
def movimientos_view(request):
    """
    Vista de movimientos con filtros seguros y paginacion
    """
    try:
        # Usar el formulario de filtros para validar inputs
        filtro_form = FiltroMovimientosForm(request.GET)
        
        # Iniciar con todos los movimientos del usuario
        movimientos = Movimiento.objects.filter(usuario=request.user)
        
        # Aplicar filtros solo si el formulario es válido
        if filtro_form.is_valid():
            cleaned_data = filtro_form.cleaned_data
            
            if cleaned_data.get('tipo'):
                movimientos = movimientos.filter(tipo=cleaned_data['tipo'])
            
            if cleaned_data.get('categoria'):
                movimientos = movimientos.filter(categoria=cleaned_data['categoria'])
            
            if cleaned_data.get('fecha_inicio'):
                movimientos = movimientos.filter(fecha__gte=cleaned_data['fecha_inicio'])
            
            if cleaned_data.get('fecha_fin'):
                movimientos = movimientos.filter(fecha__lte=cleaned_data['fecha_fin'])
            
            if cleaned_data.get('nota'):
                # Búsqueda segura en notas (sin SQL injection)
                movimientos = movimientos.filter(
                    nota__icontains=cleaned_data['nota']
                )
        else:
            # Si hay errores en filtros, mostrar mensaje
            if filtro_form.errors:
                messages.warning(request, "Algunos filtros tienen errores y fueron ignorados.")
        
        # Ordenar resultados
        movimientos = movimientos.order_by('-fecha', '-creado_en')
        
        # Paginación segura
        page = request.GET.get('page', 1)
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        
        paginator = Paginator(movimientos, 25)  # 25 por página
        
        try:
            movimientos_paginados = paginator.page(page)
        except PageNotAnInteger:
            movimientos_paginados = paginator.page(1)
        except EmptyPage:
            movimientos_paginados = paginator.page(paginator.num_pages)
        
        # Obtener categorías para el filtro
        categorias = Movimiento.objects.filter(usuario=request.user)\
                                      .values_list('categoria', flat=True)\
                                      .distinct()
        
        return render(request, 'movimientos.html', {
            'movimientos': movimientos_paginados,
            'categorias': categorias,
            'filtro_form': filtro_form,
            'total_movimientos': paginator.count,
        })
        
    except Exception as e:
        logger.error(f"Error en movimientos_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar los movimientos.")
        return render(request, 'movimientos.html', {
            'movimientos': [], 'categorias': [], 'filtro_form': FiltroMovimientosForm()
        })
    
@login_required
def resumen_view(request):
    """
    Vista de resumen mensual optimizada
    """
    try:
        # Consulta optimizada para resumen mensual
        movimientos = Movimiento.objects.filter(usuario=request.user)\
                                       .values('fecha__year', 'fecha__month', 'tipo')\
                                       .annotate(total=Sum('monto'))\
                                       .order_by('-fecha__year', '-fecha__month')
        
        # Procesar datos de forma eficiente
        resumen_dict = {}
        for mov in movimientos:
            mes_key = f"{mov['fecha__year']}-{mov['fecha__month']:02d}"
            
            if mes_key not in resumen_dict:
                resumen_dict[mes_key] = {'ingresos': 0, 'gastos': 0}
            
            if mov['tipo'] == 'ingreso':
                resumen_dict[mes_key]['ingresos'] = mov['total']
            else:
                resumen_dict[mes_key]['gastos'] = mov['total']
        
        # Convertir a lista ordenada
        resumen = []
        for mes_key, datos in resumen_dict.items():
            ingresos = datos['ingresos']
            gastos = datos['gastos']
            balance = ingresos - gastos
            
            # Crear nombre legible del mes
            año, mes = mes_key.split('-')
            try:
                mes_legible = datetime(int(año), int(mes), 1).strftime('%B %Y')
            except ValueError:
                mes_legible = mes_key  # Fallback
            
            resumen.append((mes_key, mes_legible, ingresos, gastos, balance))
        
        # Ordenar por fecha descendente
        resumen_ordenado = sorted(resumen, key=lambda x: x[0], reverse=True)
        
        return render(request, 'gastos/resumen.html', {
            'resumen': resumen_ordenado
        })
        
    except Exception as e:
        logger.error(f"Error en resumen_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar el resumen.")
        return render(request, 'gastos/resumen.html', {'resumen': []})

@login_required
def movimientos_por_mes(request, mes):
    """
    Vista para mostrar los movimientos de un mes específico.
    :param mes: str en formato 'YYYY-MM'
    """
    try:
        # Validar formato del mes de forma más robusta
        if not mes or not isinstance(mes, str):
            raise Http404("Mes no válido")
        
        # Validar formato YYYY-MM
        import re
        if not re.match(r'^\d{4}-\d{2}$', mes):
            raise Http404("Formato de mes inválido")
        
        try:
            año, mes_num = map(int, mes.split('-'))
        except ValueError:
            raise Http404("Formato de mes inválido")
        
        # Validar rangos lógicos
        if not (1900 <= año <= 2100) or not (1 <= mes_num <= 12):
            raise Http404("Fecha fuera de rango válido")
        
        # Filtrar movimientos del usuario en ese mes
        movimientos = Movimiento.objects.filter(
            usuario=request.user,
            fecha__year=año,
            fecha__month=mes_num
        ).order_by('-fecha', '-creado_en')
        
        # Calcular totales de forma eficiente
        totales = movimientos.aggregate(
            total_ingresos=Sum('monto', filter=Q(tipo='ingreso')),
            total_gastos=Sum('monto', filter=Q(tipo='gasto'))
        )
        
        ingresos = totales['total_ingresos'] or 0
        gastos = totales['total_gastos'] or 0
        balance = ingresos - gastos
        
        resumen = {
            'ingresos': ingresos,
            'gastos': gastos,
            'balance': balance,
        }
        
        # Crear nombre legible del mes
        try:
            mes_legible = datetime(año, mes_num, 1).strftime('%B %Y')
        except ValueError:
            mes_legible = mes
        
        return render(request, 'gastos/movimientos_por_mes.html', {
            'movimientos': movimientos,
            'resumen': resumen,
            'mes': mes,
            'mes_legible': mes_legible,
        })
        
    except Http404:
        # Re-raise Http404 para que Django maneje la página 404
        raise
    except Exception as e:
        logger.error(f"Error en movimientos_por_mes para usuario {request.user.id}, mes {mes}: {str(e)}")
        messages.error(request, "Error al cargar los movimientos del mes.")
        return redirect('resumen')

@login_required
@require_POST
@csrf_protect
def eliminar_movimiento(request, movimiento_id):
    """
    Vista para eliminar movimientos con validaciones de seguridad
    """
    try:
        # Validar que el ID sea un entero
        try:
            movimiento_id = int(movimiento_id)
        except (ValueError, TypeError):
            raise Http404("ID de movimiento inválido")
        
        # Obtener el movimiento y verificar propiedad
        movimiento = get_object_or_404(Movimiento, id=movimiento_id, usuario=request.user)
        
        # Log de seguridad para eliminaciones
        logger.info(f"Usuario {request.user.id} eliminó movimiento {movimiento_id}: "
                   f"{movimiento.tipo} ${movimiento.monto}")
        
        # Eliminar con transaction para atomicidad
        with transaction.atomic():
            # Guardar datos para el mensaje antes de eliminar
            monto = movimiento.monto
            tipo = movimiento.get_tipo_display()
            
            movimiento.delete()
            
            messages.success(request, 
                f"{tipo} de ${monto:,.2f} eliminado correctamente.")
        
        return redirect('movimientos')
        
    except Http404:
        messages.error(request, "El movimiento no existe o no tienes permiso para eliminarlo.")
        return redirect('movimientos')
    except Exception as e:
        logger.error(f"Error al eliminar movimiento {movimiento_id} para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al eliminar el movimiento. Intenta nuevamente.")
        return redirect('movimientos')

@login_required
@require_http_methods(["GET"])
def exportar_movimientos_pdf(request):
    """
    Vista para exportar movimientos a PDF con validaciones
    """
    try:
        # Validar límites de exportación
        total_movimientos = Movimiento.objects.filter(usuario=request.user).count()
        
        if total_movimientos > 1000:  # Límite de seguridad
            messages.error(request, 
                "Tienes demasiados movimientos para exportar. "
                "Usa los filtros para reducir la cantidad.")
            return redirect('movimientos')
        
        # Verificar últimas exportaciones (límite de rate)
        # Esto requeriría un modelo adicional para tracking, por ahora solo log
        logger.info(f"Usuario {request.user.id} exportó {total_movimientos} movimientos a PDF")
        
        movimientos = Movimiento.objects.filter(usuario=request.user)\
                                       .order_by('-fecha', '-creado_en')
        
        template = get_template("gastos/pdf_movimientos.html")
        html = template.render({
            "movimientos": movimientos,
            "usuario": request.user,
            "fecha_exportacion": timezone.now(),
        })
        
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=movimientos.pdf"
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            logger.error(f"Error generando PDF para usuario {request.user.id}")
            messages.error(request, "Error al generar el PDF. Intenta nuevamente.")
            return redirect('movimientos')
            
        return response
        
    except Exception as e:
        logger.error(f"Error en exportar_movimientos_pdf para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al exportar. Intenta nuevamente.")
        return redirect('movimientos')

@login_required
@require_http_methods(["GET"])
def exportar_pdf_mes(request, mes):
    """
    Vista para exportar PDF por mes con validaciones
    """
    try:
        # Reutilizar validaciones de movimientos_por_mes
        if not mes or not isinstance(mes, str):
            return HttpResponseBadRequest("Mes no válido")
        
        import re
        if not re.match(r'^\d{4}-\d{2}$', mes):
            return HttpResponseBadRequest("Formato de mes inválido")
        
        try:
            año, mes_num = map(int, mes.split('-'))
        except ValueError:
            return HttpResponseBadRequest("Formato de mes inválido")
        
        if not (1900 <= año <= 2100) or not (1 <= mes_num <= 12):
            return HttpResponseBadRequest("Fecha fuera de rango válido")
        
        # Obtener movimientos del mes
        movimientos = Movimiento.objects.filter(
            usuario=request.user,
            fecha__year=año,
            fecha__month=mes_num
        ).order_by('fecha', 'creado_en')
        
        if not movimientos.exists():
            messages.info(request, "No hay movimientos en ese mes para exportar.")
            return redirect('resumen')
        
        # Log de exportación
        logger.info(f"Usuario {request.user.id} exportó mes {mes} con {movimientos.count()} movimientos")
        
        mes_legible = datetime(año, mes_num, 1).strftime('%B %Y')
        
        template = get_template('gastos/pdf_por_mes.html')
        html = template.render({
            'movimientos': movimientos, 
            'mes_legible': mes_legible,
            'usuario': request.user,
            'fecha_exportacion': timezone.now(),
        })
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{mes}_movimientos.pdf"'
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            logger.error(f"Error generando PDF del mes {mes} para usuario {request.user.id}")
            messages.error(request, "Error al generar el PDF del mes.")
            return redirect('resumen')
        
        return response
        
    except Exception as e:
        logger.error(f"Error en exportar_pdf_mes para usuario {request.user.id}, mes {mes}: {str(e)}")
        messages.error(request, "Error al exportar el mes.")
        return redirect('resumen')
