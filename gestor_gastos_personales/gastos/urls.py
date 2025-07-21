from django.urls import path
from .views import balance_view
from . import views

urlpatterns = [
    path('balance/', balance_view, name='balance'),
    path('crear/', views.crear_movimiento_view, name='crear_movimiento'),
    path('movimientos/', views.movimientos_view, name='movimientos'),
]