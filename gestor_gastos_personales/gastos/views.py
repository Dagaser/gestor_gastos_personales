from django.shortcuts import render
from django.db import models
from .models import Movimiento
from django.contrib.auth.decorators import login_required

@login_required
def balance_view(request):
    movimientos = Movimiento.objects.filter(usuario=request.user)
    ingresos = movimientos.filter(tipo='ingeso').aggregate(total=models.Sum('monto'))['total'] or 0
    gastos = movimientos.filter(tipo='gasto').aggregate(total=models.Sum('monto'))['total'] or 0
    balance = ingresos - gastos

    contexto = {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance
    }

    return render(request,'gastos/balance.html', contexto)
