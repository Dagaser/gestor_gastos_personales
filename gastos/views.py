from django.shortcuts import render, redirect
from django.db import models
from .models import Movimiento
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .forms import MovimientoForm
from django.db.models.functions import TruncMonth
from collections import defaultdict
from django.utils.timezone import now
from datetime import datetime

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
    movimientos = Movimiento.objects.filter(usuario=request.user)  # Obtiene todos los movimientos del ususario autenticado.
    resumen = defaultdict(lambda: {'ingresos': 0, 'gastos': 0})     # Agrupar por mes y año.
    
    for mov in movimientos:
        mes_ano = mov.fecha.strftime('%B %Y')
        if mov.tipo == 'ingreso':
            resumen[mes_ano]['ingresos'] += mov.monto
        elif mov.tipo == 'gasto':
            resumen[mes_ano]['gastos'] += mov.monto
    
    # Calcular balance
    for mes_ano in resumen:
        ingresos = resumen[mes_ano]['ingresos']
        gastos = resumen[mes_ano]['gastos']
        resumen[mes_ano]['balance'] = ingresos - gastos

    # Ordenar por fecha descendente
    resumen_ordenado = sorted(
        resumen.items(),
        key=lambda x: datetime.strptime(x[0], '%B %Y'),
        reverse=True
    )

    return render(request, 'gastos/resumen.html', {
        'resumen': resumen_ordenado
    })