from django.urls import path
from .views import balance_view, home_view, dashboard_view, editar_movimiento_view, estadisticas_view, notificaciones_view, exportar_movimientos_excel, presupuestos_view, crear_presupuesto_view, editar_presupuesto_view, eliminar_presupuesto
from . import views

urlpatterns = [
    path('', home_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('balance/', balance_view, name='balance'),
    path('crear/', views.crear_movimiento_view, name='crear_movimiento'),
    path('movimientos/', views.movimientos_view, name='movimientos'),
    path('resumen/', views.resumen_view, name='resumen'),
    path('estadisticas/', estadisticas_view, name='estadisticas'),
    path('notificaciones/', notificaciones_view, name='notificaciones'),
    path('presupuestos/', presupuestos_view, name='presupuestos'),
    path('presupuestos/crear/', crear_presupuesto_view, name='crear_presupuesto'),
    path('presupuestos/editar/<int:presupuesto_id>/', editar_presupuesto_view, name='editar_presupuesto'),
    path('presupuestos/eliminar/<int:presupuesto_id>/', eliminar_presupuesto, name='eliminar_presupuesto'),
    path('editar/<int:movimiento_id>/', editar_movimiento_view, name='editar_movimiento'),
    path('eliminar/<int:movimiento_id>/', views.eliminar_movimiento, name='eliminar_movimiento'),
    path("exportar-pdf/", views.exportar_movimientos_pdf, name="exportar_movimientos_pdf"),
    path("exportar-excel/", exportar_movimientos_excel, name="exportar_movimientos_excel"),
    path('resumen/<str:mes>/pdf/', views.exportar_pdf_mes, name='exportar_pdf_mes'),
    path('resumen/<str:mes>/', views.movimientos_por_mes, name='movimientos_por_mes'),

]