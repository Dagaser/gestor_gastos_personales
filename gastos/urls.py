from django.urls import path
from .views import balance_view
from . import views

urlpatterns = [
    path('balance/', balance_view, name='balance'),
    path('crear/', views.crear_movimiento_view, name='crear_movimiento'),
    path('movimientos/', views.movimientos_view, name='movimientos'),
    path('resumen/', views.resumen_view, name='resumen'),
    path('eliminar/<int:movimiento_id>/', views.eliminar_movimiento, name='eliminar_movimiento'),
    path("exportar-pdf/", views.exportar_movimientos_pdf, name="exportar_movimientos_pdf"),
    path('resumen/<str:mes>/pdf/', views.exportar_pdf_mes, name='exportar_pdf_mes'),
    path('resumen/<str:mes>/', views.movimientos_por_mes, name='movimientos_por_mes'),

]