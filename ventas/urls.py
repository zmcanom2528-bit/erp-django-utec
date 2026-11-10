# ventas/urls.py
"""URLs de la app ventas — W02 (inicio) + W07 (lectura) + W08 (escritura)."""
from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.VentaListView.as_view(), name='lista'),
    path('nueva/', views.crear_venta, name='crear'),
    path('<int:venta_id>/', views.VentaDetailView.as_view(), name='detalle'),
    path('<int:venta_id>/eliminar/', views.VentaDeleteView.as_view(), name='eliminar'),
    # Página de módulo W02
    path('inicio/',
         TemplateView.as_view(
             template_name='ventas/index.html',
             extra_context={
                 'titulo': 'Ventas',
                 'descripcion': 'Ciclo de ventas, pedidos y facturación.',
                 'espiral': 'Espiral 3 · W07',
             }),
         name='inicio'),
]
