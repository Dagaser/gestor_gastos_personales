from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from .models import Movimiento
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .forms import MovimientoForm
from django.db.models.functions import TruncMonth
from collections import defaultdict
from django.utils.timezone import now
from datetime import datetime
from django.contrib import messages
from django.template.loader import get_template, render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa 
from calendar import monthrange
import tempfile
from weasyprint import HTML

@login_required
def balance_view(request):
    movimientos = Movimiento.objects.filter(usuario=request.user)
    ingresos = movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
    gastos = movimientos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
    balance = ingresos - gastos

    contexto = {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance,
        'movimientos': movimientos.order_by('-fecha')[:10],
    }

    return render(request,'gastos/balance.html', contexto)

@login_required
def crear_movimiento_view(request):
    if request.method == 'POST':
        form = MovimientoForm(request.POST, request.FILES)

        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user
            movimiento.creado_en = now()
            movimiento.save()
            return redirect('balance')
        
    else:
        form = MovimientoForm()

    return render(request, 'crear_movimiento.html', {'form': form})

@login_required
def movimientos_view(request):
    movimientos = Movimiento.objects.filter(usuario=request.user).order_by('-fecha')
    
    tipo = request.GET.get('tipo')
    categoria = request.GET.get('categoria')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    nota = request.GET.get('nota')

    if tipo:
        movimientos = movimientos.filter(tipo=tipo)

    if categoria:
        movimientos = movimientos.filter(categoria__iexact=categoria)

    if fecha_inicio:
        movimientos = movimientos.filter(fecha__gte=fecha_inicio)
    
    if fecha_fin:
        movimientos = movimientos.filter(fecha__lte=fecha_fin)
    
    if nota:
        movimientos = movimientos.filter(nota__icontains=nota)
    
    categorias = Movimiento.objects.filter(usuario=request.user)\
                                .values_list('categoria', flat=True)\
                                .distinct()
    
    return render(request, 'movimientos.html', {
        'movimientos': movimientos,
        'categorias': categorias,
        'filtros': {
            'tipo': tipo,
            'categoria': categoria,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'nota': nota,
        }
    })

@login_required
def resumen_view(request):
    movimientos = Movimiento.objects.filter(usuario=request.user)
    resumen_temp = defaultdict(lambda: {'ingresos': 0, 'gastos': 0})

    for mov in movimientos:
        mes_key = mov.fecha.strftime('%Y-%m')  # Ej: '2025-07' → para URL
        if mov.tipo == 'ingreso':
            resumen_temp[mes_key]['ingresos'] += mov.monto
        elif mov.tipo == 'gasto':
            resumen_temp[mes_key]['gastos'] += mov.monto

    # Armar resumen con clave y nombre legible
    resumen = []
    for mes_key, datos in resumen_temp.items():
        ingresos = datos['ingresos']
        gastos = datos['gastos']
        balance = ingresos - gastos
        mes_legible = datetime.strptime(mes_key, '%Y-%m').strftime('%B %Y')  # Ej: 'Julio 2025'
        resumen.append((mes_key, mes_legible, ingresos, gastos, balance))

    # Ordenar por mes_key descendente
    resumen_ordenado = sorted(resumen, key=lambda x: x[0], reverse=True)

    return render(request, 'gastos/resumen.html', {
        'resumen': resumen_ordenado
    })

@login_required
def movimientos_por_mes(request, mes):
    """
    Vista para mostrar los movimientos de un mes específico.
    :param mes: str en formato 'YYYY-MM'
    """
    try:
        # Convertir la cadena '2025-07' en año y mes enteros
        año, mes_num = map(int, mes.split('-'))
    except ValueError:
        return render(request, 'error.html', {'mensaje': 'Formato de mes inválido.'})

    # Filtrar movimientos del usuario en ese mes
    movimientos = Movimiento.objects.filter(
        usuario=request.user,
        fecha__year=año,
        fecha__month=mes_num
    )

    # Calcular ingresos y gastos del mes
    ingresos = sum(m.monto for m in movimientos if m.tipo == 'ingreso')
    gastos = sum(m.monto for m in movimientos if m.tipo == 'gasto')
    balance = ingresos - gastos

    resumen = {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance,
    }

    # Mostrar el mes en formato legible
    mes_legible = datetime(año, mes_num, 1).strftime('%B %Y')  # Ej: Julio 2025

    return render(request, 'gastos/movimientos_por_mes.html', {
        'movimientos': movimientos,
        'resumen': resumen,
        'mes': mes,
        'mes_legible': mes_legible,
    })

@login_required
def eliminar_movimiento(request, movimiento_id):
    movimiento = get_object_or_404(Movimiento, id=movimiento_id, usuario=request.user)
    movimiento.delete()
    messages.success(request, "Movimiento eliminado correctamente.")
    return redirect('movimientos')

def exportar_movimientos_pdf(request):
    movimientos = Movimiento.objects.filter(usuario=request.user)

    template = get_template("gastos/pdf_movimientos.html")
    html = template.render({"movimientos": movimientos})
    
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=movimientos.pdf"
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error al generar PDF", status=500)
    return response

@login_required
def exportar_pdf_mes(request, mes):
    try:
        # Parsear mes en formato YYYY-MM
        año, mes_num = map(int, mes.split('-'))
    except ValueError:
        return HttpResponse("Formato de fecha inválido", status=400)

    # Filtrar movimientos del mes y usuario
    inicio_mes = datetime(año, mes_num, 1)
    fin_mes = datetime(año, mes_num, monthrange(año, mes_num)[1])
    
    movimientos = Movimiento.objects.filter(
        usuario=request.user,
        fecha__range=(inicio_mes, fin_mes)
    ).order_by('fecha')

    # Calcular resumen
    ingresos = sum(m.monto for m in movimientos if m.tipo == 'ingreso')
    gastos = sum(m.monto for m in movimientos if m.tipo == 'gasto')
    balance = ingresos - gastos

    mes_legible = inicio_mes.strftime('%B %Y')

    html_string = render_to_string("gastos/pdf_por_mes.html", {
        "movimientos": movimientos,
        "mes": mes_legible,
        "resumen": {
            "ingresos": ingresos,
            "gastos": gastos,
            "balance": balance
        }
    })

    # Convertir HTML a PDF usando WeasyPrint y devolverlo como descarga
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="movimientos_{mes}.pdf"'

    with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
        HTML(string=html_string).write_pdf(tmp_file.name)
        tmp_file.seek(0)
        response.write(tmp_file.read())

    return response