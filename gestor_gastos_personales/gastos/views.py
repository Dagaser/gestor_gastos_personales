from django.shortcuts import render, redirect
from django.db import models
from .models import Movimiento
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .forms import MovimientoForm


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
        form = MovimientoForm(request.POST)

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
    return render(request, 'movimientos.html', {'movimientos': movimientos})
