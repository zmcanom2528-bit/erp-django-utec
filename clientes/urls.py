# clientes/urls.py
"""URLs de la app clientes — W02 (inicio) + W07 (lectura) + W08 (escritura)."""
from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.ClienteListView.as_view(), name='lista'),
    path('<int:cliente_id>/', views.ClienteDetailView.as_view(), name='detalle'),
    path('nuevo/', views.ClienteCreateView.as_view(), name='crear'),
    path('<int:cliente_id>/editar/', views.ClienteUpdateView.as_view(), name='editar'),
    path('<int:cliente_id>/eliminar/', views.ClienteDeleteView.as_view(), name='eliminar'),
    # Página de módulo W02 (la exigen test_w02_mvt y el navbar de base.html)
    path('inicio/',
         TemplateView.as_view(
             template_name='clientes/index.html',
             extra_context={
                 'titulo': 'Clientes',
                 'descripcion': 'Gestión de cartera de clientes.',
                 'espiral': 'Espiral 2 · W04',
             }),
         name='inicio'),
]
