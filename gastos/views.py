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

@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def editar_movimiento_view(request, movimiento_id):
    """
    Vista para editar movimientos existentes
    """
    try:
        # Obtener el movimiento y verificar propiedad
        movimiento = get_object_or_404(Movimiento, id=movimiento_id, usuario=request.user)
        
        if request.method == 'POST':
            form = MovimientoForm(request.POST, request.FILES, instance=movimiento)
            if form.is_valid():
                try:
                    # Guardar cambios
                    form.save()
                    
                    messages.success(request, 'Movimiento actualizado exitosamente')
                    return redirect('movimientos')
                    
                except Exception as e:
                    messages.error(request, f'Error al actualizar movimiento: {e}')
                    return render(request, 'editar_movimiento.html', {'form': form, 'movimiento': movimiento})
        else:
            form = MovimientoForm(instance=movimiento)
        
        context = {
            'form': form,
            'movimiento': movimiento,
            'titulo': 'Editar Movimiento'
        }
        return render(request, 'editar_movimiento.html', context)
        
    except Http404:
        messages.error(request, "El movimiento no existe o no tienes permiso para editarlo.")
        return redirect('movimientos')
    except Exception as e:
        logger.error(f"Error en editar_movimiento_view para usuario {request.user.id}, movimiento {movimiento_id}: {str(e)}")
        messages.error(request, "Error al cargar el movimiento para editar.")
        return redirect('movimientos')

@login_required
def home_view(request):
    """
    Vista principal que redirige al balance
    """
    return redirect('balance')

@login_required
def dashboard_view(request):
    """
    Dashboard con estadísticas avanzadas y gráficos
    """
    try:
        # Obtener datos del usuario
        movimientos = Movimiento.objects.filter(usuario=request.user)
        
        # Estadísticas generales
        total_ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        total_gastos = movimientos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        balance = total_ingresos - total_gastos
        
        # Movimientos del mes actual
        mes_actual = timezone.now().month
        año_actual = timezone.now().year
        
        movimientos_mes = movimientos.filter(
            fecha__year=año_actual,
            fecha__month=mes_actual
        )
        
        ingresos_mes = movimientos_mes.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        gastos_mes = movimientos_mes.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        balance_mes = ingresos_mes - gastos_mes
        
        # Top categorías de gastos
        top_categorias = movimientos.filter(tipo='gasto')\
                                   .values('categoria')\
                                   .annotate(total=Sum('monto'))\
                                   .order_by('-total')[:5]
        
        # Últimos movimientos
        ultimos_movimientos = movimientos.order_by('-fecha', '-creado_en')[:10]
        
        # Estadísticas por mes (últimos 6 meses)
        meses_stats = []
        for i in range(6):
            fecha = timezone.now() - timedelta(days=30*i)
            movs_mes = movimientos.filter(
                fecha__year=fecha.year,
                fecha__month=fecha.month
            )
            ingresos = movs_mes.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
            gastos = movs_mes.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
            
            meses_stats.append({
                'mes': fecha.strftime('%B %Y'),
                'ingresos': ingresos,
                'gastos': gastos,
                'balance': ingresos - gastos
            })
        
        contexto = {
            'total_ingresos': total_ingresos,
            'total_gastos': total_gastos,
            'balance': balance,
            'ingresos_mes': ingresos_mes,
            'gastos_mes': gastos_mes,
            'balance_mes': balance_mes,
            'top_categorias': top_categorias,
            'ultimos_movimientos': ultimos_movimientos,
            'meses_stats': meses_stats,
            'total_movimientos': movimientos.count(),
        }
        
        return render(request, 'gastos/dashboard.html', contexto)
        
    except Exception as e:
        logger.error(f"Error en dashboard_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar el dashboard.")
        return render(request, 'gastos/dashboard.html', {})

@login_required
def estadisticas_view(request):
    """
    Vista para estadísticas avanzadas y análisis
    """
    try:
        # Obtener datos del usuario
        movimientos = Movimiento.objects.filter(usuario=request.user)
        
        # Estadísticas por año
        año_actual = timezone.now().year
        movimientos_año = movimientos.filter(fecha__year=año_actual)
        
        # Gastos por mes del año actual
        gastos_por_mes = []
        for mes in range(1, 13):
            gastos_mes = movimientos_año.filter(
                fecha__month=mes,
                tipo='gasto'
            ).aggregate(total=Sum('monto'))['total'] or 0
            gastos_por_mes.append({
                'mes': mes,
                'nombre_mes': datetime(año_actual, mes, 1).strftime('%B'),
                'total': gastos_mes
            })
        
        # Ingresos por mes del año actual
        ingresos_por_mes = []
        for mes in range(1, 13):
            ingresos_mes = movimientos_año.filter(
                fecha__month=mes,
                tipo='ingreso'
            ).aggregate(total=Sum('monto'))['total'] or 0
            ingresos_por_mes.append({
                'mes': mes,
                'nombre_mes': datetime(año_actual, mes, 1).strftime('%B'),
                'total': ingresos_mes
            })
        
        # Top 5 categorías de gastos
        top_categorias_gastos = movimientos.filter(tipo='gasto')\
                                          .values('categoria')\
                                          .annotate(total=Sum('monto'))\
                                          .order_by('-total')[:5]
        
        # Promedio de gastos por día
        total_gastos = movimientos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        dias_con_gastos = movimientos.filter(tipo='gasto').values('fecha').distinct().count()
        promedio_diario = total_gastos / dias_con_gastos if dias_con_gastos > 0 else 0
        
        # Calcular total de ingresos para estadísticas
        total_ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        # Movimientos más grandes
        movimientos_grandes = movimientos.order_by('-monto')[:10]
        
        # Tendencia de ahorro (últimos 6 meses)
        tendencia_ahorro = []
        for i in range(6):
            fecha = timezone.now() - timedelta(days=30*i)
            movs_mes = movimientos.filter(
                fecha__year=fecha.year,
                fecha__month=fecha.month
            )
            ingresos = movs_mes.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
            gastos = movs_mes.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
            ahorro = ingresos - gastos
            
            tendencia_ahorro.append({
                'mes': fecha.strftime('%B %Y'),
                'ingresos': ingresos,
                'gastos': gastos,
                'ahorro': ahorro,
                'porcentaje_ahorro': (ahorro / ingresos * 100) if ingresos > 0 else 0
            })
        
        contexto = {
            'año_actual': año_actual,
            'gastos_por_mes': gastos_por_mes,
            'ingresos_por_mes': ingresos_por_mes,
            'top_categorias_gastos': top_categorias_gastos,
            'promedio_diario': promedio_diario,
            'movimientos_grandes': movimientos_grandes,
            'tendencia_ahorro': tendencia_ahorro,
            'total_movimientos': movimientos.count(),
            'total_gastos': total_gastos,
            'total_ingresos': total_ingresos,
            'dias_con_gastos': dias_con_gastos,
        }
        
        return render(request, 'gastos/estadisticas.html', contexto)
        
    except Exception as e:
        logger.error(f"Error en estadisticas_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar las estadísticas.")
        return render(request, 'gastos/estadisticas.html', {})

@login_required
def notificaciones_view(request):
    """
    Vista para mostrar notificaciones y alertas del usuario
    """
    try:
        # Obtener datos del usuario
        movimientos = Movimiento.objects.filter(usuario=request.user)
        
        # Alertas y notificaciones
        alertas = []
        
        # 1. Verificar si hay movimientos grandes recientes
        movimientos_grandes = movimientos.filter(
            monto__gte=1000000,  # Más de 1 millón
            fecha__gte=timezone.now().date() - timedelta(days=7)
        )
        
        if movimientos_grandes.exists():
            alertas.append({
                'tipo': 'warning',
                'titulo': 'Movimientos Grandes Recientes',
                'mensaje': f'Tienes {movimientos_grandes.count()} movimiento(s) grande(s) en los últimos 7 días.',
                'icono': '💰'
            })
        
        # 2. Verificar si no hay ingresos este mes
        mes_actual = timezone.now().month
        año_actual = timezone.now().year
        ingresos_mes = movimientos.filter(
            fecha__year=año_actual,
            fecha__month=mes_actual,
            tipo='ingreso'
        ).count()
        
        if ingresos_mes == 0:
            alertas.append({
                'tipo': 'info',
                'titulo': 'Sin Ingresos Este Mes',
                'mensaje': 'No has registrado ingresos este mes. ¿Olvidaste registrar tu salario?',
                'icono': '📅'
            })
        
        # 3. Verificar si hay muchos gastos en un día
        gastos_hoy = movimientos.filter(
            fecha=timezone.now().date(),
            tipo='gasto'
        ).count()
        
        if gastos_hoy > 5:
            alertas.append({
                'tipo': 'warning',
                'titulo': 'Muchos Gastos Hoy',
                'mensaje': f'Has registrado {gastos_hoy} gastos hoy. Revisa si todos son necesarios.',
                'icono': '⚠️'
            })
        
        # 4. Verificar si no hay movimientos en varios días
        ultimo_movimiento = movimientos.order_by('-fecha').first()
        if ultimo_movimiento:
            dias_sin_movimientos = (timezone.now().date() - ultimo_movimiento.fecha).days
            if dias_sin_movimientos > 7:
                alertas.append({
                    'tipo': 'info',
                    'titulo': 'Sin Movimientos Recientes',
                    'mensaje': f'No has registrado movimientos en {dias_sin_movimientos} días.',
                    'icono': '📝'
                })
        
        # 5. Verificar balance negativo
        total_ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        total_gastos = movimientos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        balance = total_ingresos - total_gastos
        
        if balance < 0:
            alertas.append({
                'tipo': 'danger',
                'titulo': 'Balance Negativo',
                'mensaje': f'Tu balance actual es negativo: ${abs(balance):,.0f}. Considera revisar tus gastos.',
                'icono': '🔴'
            })
        
        # 6. Verificar si hay categorías con muchos gastos
        categoria_mas_gastos = movimientos.filter(tipo='gasto')\
                                         .values('categoria')\
                                         .annotate(total=Sum('monto'))\
                                         .order_by('-total')\
                                         .first()
        
        if categoria_mas_gastos and float(categoria_mas_gastos['total']) > float(total_gastos) * 0.5:
            alertas.append({
                'tipo': 'warning',
                'titulo': 'Categoría con Muchos Gastos',
                'mensaje': f'La categoría "{categoria_mas_gastos["categoria"]}" representa más del 50% de tus gastos.',
                'icono': '📊'
            })
        
        # Consejos personalizados
        consejos = [
            {
                'titulo': '💡 Consejo del Día',
                'mensaje': 'Revisa tus gastos semanalmente para identificar patrones y oportunidades de ahorro.',
                'tipo': 'info'
            },
            {
                'titulo': '🎯 Meta Sugerida',
                'mensaje': 'Intenta ahorrar al menos el 20% de tus ingresos cada mes.',
                'tipo': 'success'
            }
        ]
        
        # Si no hay alertas, mostrar mensaje positivo
        if not alertas:
            alertas.append({
                'tipo': 'success',
                'titulo': '¡Excelente Gestión!',
                'mensaje': 'Tu gestión financiera se ve muy bien. ¡Sigue así!',
                'icono': '🎉'
            })
        
        contexto = {
            'alertas': alertas,
            'consejos': consejos,
            'total_alertas': len(alertas),
            'balance': balance,
            'total_movimientos': movimientos.count(),
        }
        
        return render(request, 'gastos/notificaciones.html', contexto)
        
    except Exception as e:
        logger.error(f"Error en notificaciones_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar las notificaciones.")
        return render(request, 'gastos/notificaciones.html', {})

@login_required
@require_http_methods(["GET"])
def exportar_movimientos_excel(request):
    """
    Vista para exportar movimientos a Excel
    """
    try:
        # Validar límites de exportación
        total_movimientos = Movimiento.objects.filter(usuario=request.user).count()
        
        if total_movimientos > 1000:  # Límite de seguridad
            messages.error(request, 
                "Tienes demasiados movimientos para exportar. "
                "Usa los filtros para reducir la cantidad.")
            return redirect('movimientos')
        
        # Obtener movimientos
        movimientos = Movimiento.objects.filter(usuario=request.user)\
                                       .order_by('-fecha', '-creado_en')
        
        # Crear respuesta Excel
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Movimientos"
        
        # Estilos
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        center_alignment = Alignment(horizontal="center", vertical="center")
        
        # Encabezados
        headers = [
            'ID', 'Fecha', 'Tipo', 'Categoría', 'Descripción', 
            'Monto', 'Nota', 'Comprobante', 'Creado En', 'Actualizado En'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
        
        # Datos
        for row, movimiento in enumerate(movimientos, 2):
            ws.cell(row=row, column=1, value=movimiento.id)
            ws.cell(row=row, column=2, value=movimiento.fecha)
            ws.cell(row=row, column=3, value=movimiento.get_tipo_display())
            ws.cell(row=row, column=4, value=movimiento.get_categoria_display())
            ws.cell(row=row, column=5, value=movimiento.descripcion)
            ws.cell(row=row, column=6, value=float(movimiento.monto))
            ws.cell(row=row, column=7, value=movimiento.nota or '')
            ws.cell(row=row, column=8, value='Sí' if movimiento.comprobante else 'No')
            # Convertir timezone-aware a naive para Excel
            ws.cell(row=row, column=9, value=movimiento.creado_en.replace(tzinfo=None) if movimiento.creado_en else None)
            ws.cell(row=row, column=10, value=movimiento.actualizado_en.replace(tzinfo=None) if movimiento.actualizado_en else None)
        
        # Ajustar ancho de columnas
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15
        
        # Crear hoja de resumen
        ws2 = wb.create_sheet("Resumen")
        
        # Estadísticas en la hoja de resumen
        total_ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        total_gastos = movimientos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        balance = total_ingresos - total_gastos
        
        resumen_data = [
            ['Estadísticas Generales', ''],
            ['Total Movimientos', total_movimientos],
            ['Total Ingresos', f'${total_ingresos:,.2f}'],
            ['Total Gastos', f'${total_gastos:,.2f}'],
            ['Balance', f'${balance:,.2f}'],
            ['', ''],
            ['Resumen por Categoría', ''],
        ]
        
        # Resumen por categoría
        categorias = movimientos.values('categoria')\
                               .annotate(total=Sum('monto'), count=models.Count('id'))\
                               .order_by('-total')
        
        for cat in categorias:
            resumen_data.append([
                cat['categoria'].title(),
                f"${cat['total']:,.2f} ({cat['count']} movimientos)"
            ])
        
        # Escribir datos de resumen
        for row, (col1, col2) in enumerate(resumen_data, 1):
            ws2.cell(row=row, column=1, value=col1)
            ws2.cell(row=row, column=2, value=col2)
            
            # Aplicar estilos a encabezados
            if col1 in ['Estadísticas Generales', 'Resumen por Categoría']:
                cell = ws2.cell(row=row, column=1)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        
        # Ajustar ancho de columnas en resumen
        ws2.column_dimensions['A'].width = 25
        ws2.column_dimensions['B'].width = 30
        
        # Log de exportación
        logger.info(f"Usuario {request.user.id} exportó {total_movimientos} movimientos a Excel")
        
        # Crear respuesta
        from django.http import HttpResponse
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="movimientos_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        wb.save(response)
        return response
        
    except ImportError:
        messages.error(request, 
            "La exportación a Excel requiere la librería 'openpyxl'. "
            "Instálala con: pip install openpyxl")
        return redirect('movimientos')
    except Exception as e:
        logger.error(f"Error en exportar_movimientos_excel para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al exportar a Excel. Intenta nuevamente.")
        return redirect('movimientos')

@login_required
def presupuestos_view(request):
    """
    Vista para listar y gestionar presupuestos
    """
    try:
        from .forms import FiltroPresupuestosForm
        from .models import Presupuesto
        
        # Usar formulario de filtros
        filtro_form = FiltroPresupuestosForm(request.GET)
        
        # Iniciar con todos los presupuestos del usuario
        presupuestos = Presupuesto.objects.filter(usuario=request.user)
        
        # Aplicar filtros
        if filtro_form.is_valid():
            cleaned_data = filtro_form.cleaned_data
            
            if cleaned_data.get('año'):
                presupuestos = presupuestos.filter(año=cleaned_data['año'])
            
            if cleaned_data.get('mes'):
                presupuestos = presupuestos.filter(mes=cleaned_data['mes'])
            
            if cleaned_data.get('categoria'):
                presupuestos = presupuestos.filter(categoria=cleaned_data['categoria'])
            
            if cleaned_data.get('estado'):
                # Filtrar por estado (propiedad calculada)
                if cleaned_data['estado'] == 'excedido':
                    presupuestos = presupuestos.filter(
                        monto_gastado__gte=models.F('monto_presupuestado')
                    )
                elif cleaned_data['estado'] == 'advertencia':
                    presupuestos = presupuestos.filter(
                        monto_gastado__gte=models.F('monto_presupuestado') * 0.8,
                        monto_gastado__lt=models.F('monto_presupuestado')
                    )
                elif cleaned_data['estado'] == 'normal':
                    presupuestos = presupuestos.filter(
                        monto_gastado__lt=models.F('monto_presupuestado') * 0.8
                    )
        
        # Actualizar montos gastados antes de mostrar
        for presupuesto in presupuestos:
            presupuesto.actualizar_gastado()
        
        # Ordenar resultados
        presupuestos = presupuestos.order_by('-año', '-mes', 'categoria')
        
        # Paginación
        page = request.GET.get('page', 1)
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        
        paginator = Paginator(presupuestos, 20)
        
        try:
            presupuestos_paginados = paginator.page(page)
        except PageNotAnInteger:
            presupuestos_paginados = paginator.page(1)
        except EmptyPage:
            presupuestos_paginados = paginator.page(paginator.num_pages)
        
        # Estadísticas de presupuestos
        total_presupuestado = presupuestos.aggregate(
            total=models.Sum('monto_presupuestado')
        )['total'] or 0
        total_gastado = presupuestos.aggregate(
            total=models.Sum('monto_gastado')
        )['total'] or 0
        presupuestos_excedidos = presupuestos.filter(
            monto_gastado__gte=models.F('monto_presupuestado')
        ).count()
        
        return render(request, 'gastos/presupuestos.html', {
            'presupuestos': presupuestos_paginados,
            'filtro_form': filtro_form,
            'total_presupuestado': total_presupuestado,
            'total_gastado': total_gastado,
            'presupuestos_excedidos': presupuestos_excedidos,
            'total_presupuestos': paginator.count,
        })
        
    except Exception as e:
        logger.error(f"Error en presupuestos_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar los presupuestos.")
        return render(request, 'gastos/presupuestos.html', {
            'presupuestos': [], 'filtro_form': FiltroPresupuestosForm()
        })

@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def crear_presupuesto_view(request):
    """
    Vista para crear nuevos presupuestos
    """
    try:
        from .forms import PresupuestoForm
        from .models import Presupuesto
        
        # Obtener año y mes actual o de la URL
        año = request.GET.get('año', timezone.now().year)
        mes = request.GET.get('mes', timezone.now().month)
        
        try:
            año = int(año)
            mes = int(mes)
        except (ValueError, TypeError):
            año = timezone.now().year
            mes = timezone.now().month
        
        if request.method == 'POST':
            form = PresupuestoForm(
                request.POST, 
                usuario=request.user, 
                año=año, 
                mes=mes
            )
            if form.is_valid():
                try:
                    presupuesto = form.save(commit=False)
                    presupuesto.usuario = request.user
                    presupuesto.año = año
                    presupuesto.mes = mes
                    presupuesto.save()
                    
                    messages.success(request, 'Presupuesto creado exitosamente')
                    return redirect('presupuestos')
                    
                except Exception as e:
                    messages.error(request, f'Error al crear presupuesto: {e}')
                    return render(request, 'gastos/crear_presupuesto.html', {'form': form})
        else:
            form = PresupuestoForm(usuario=request.user, año=año, mes=mes)
        
        context = {
            'form': form,
            'año': año,
            'mes': mes,
            'mes_nombre': datetime(año, mes, 1).strftime('%B %Y'),
            'titulo': 'Crear Presupuesto'
        }
        return render(request, 'gastos/crear_presupuesto.html', context)
        
    except Exception as e:
        logger.error(f"Error en crear_presupuesto_view para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al cargar el formulario de presupuesto.")
        return redirect('presupuestos')

@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def editar_presupuesto_view(request, presupuesto_id):
    """
    Vista para editar presupuestos existentes
    """
    try:
        from .forms import PresupuestoForm
        from .models import Presupuesto
        
        presupuesto = get_object_or_404(Presupuesto, id=presupuesto_id, usuario=request.user)
        
        if request.method == 'POST':
            form = PresupuestoForm(
                request.POST, 
                instance=presupuesto,
                usuario=request.user, 
                año=presupuesto.año, 
                mes=presupuesto.mes
            )
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Presupuesto actualizado exitosamente')
                    return redirect('presupuestos')
                    
                except Exception as e:
                    messages.error(request, f'Error al actualizar presupuesto: {e}')
                    return render(request, 'gastos/editar_presupuesto.html', {'form': form, 'presupuesto': presupuesto})
        else:
            form = PresupuestoForm(
                instance=presupuesto,
                usuario=request.user, 
                año=presupuesto.año, 
                mes=presupuesto.mes
            )
        
        context = {
            'form': form,
            'presupuesto': presupuesto,
            'titulo': 'Editar Presupuesto'
        }
        return render(request, 'gastos/editar_presupuesto.html', context)
        
    except Http404:
        messages.error(request, "El presupuesto no existe o no tienes permiso para editarlo.")
        return redirect('presupuestos')
    except Exception as e:
        logger.error(f"Error en editar_presupuesto_view para usuario {request.user.id}, presupuesto {presupuesto_id}: {str(e)}")
        messages.error(request, "Error al cargar el presupuesto para editar.")
        return redirect('presupuestos')

@login_required
@require_POST
@csrf_protect
def eliminar_presupuesto(request, presupuesto_id):
    """
    Vista para eliminar presupuestos
    """
    try:
        from .models import Presupuesto
        
        presupuesto = get_object_or_404(Presupuesto, id=presupuesto_id, usuario=request.user)
        
        # Log de seguridad
        logger.info(f"Usuario {request.user.id} eliminó presupuesto {presupuesto_id}: "
                   f"{presupuesto.get_categoria_display()} ${presupuesto.monto_presupuestado}")
        
        with transaction.atomic():
            categoria = presupuesto.get_categoria_display()
            monto = presupuesto.monto_presupuestado
            presupuesto.delete()
            
            messages.success(request, 
                f"Presupuesto de {categoria} (${monto:,.2f}) eliminado correctamente.")
        
        return redirect('presupuestos')
        
    except Http404:
        messages.error(request, "El presupuesto no existe o no tienes permiso para eliminarlo.")
        return redirect('presupuestos')
    except Exception as e:
        logger.error(f"Error al eliminar presupuesto {presupuesto_id} para usuario {request.user.id}: {str(e)}")
        messages.error(request, "Error al eliminar el presupuesto. Intenta nuevamente.")
        return redirect('presupuestos')
