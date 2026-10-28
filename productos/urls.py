# productos/urls.py
"""URLs de la app productos — W08 (CRUD completo)."""
from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'productos'

urlpatterns = [
    # Inicio del módulo (lo usa base.html y test_w02_mvt)
    path('inicio/',
         TemplateView.as_view(template_name='productos/index.html'),
         name='inicio'),
    # Lectura (W07)
    path('',
         views.ProductoListView.as_view(),
         name='lista'),
    path('<int:producto_id>/',
         views.ProductoDetailView.as_view(),
         name='detalle'),
    # Escritura (W08)
    path('nuevo/',
         views.ProductoCreateView.as_view(),
         name='crear'),
    path('<int:producto_id>/editar/',
         views.ProductoUpdateView.as_view(),
         name='editar'),
    path('<int:producto_id>/eliminar/',
         views.ProductoDeleteView.as_view(),
         name='eliminar'),
]