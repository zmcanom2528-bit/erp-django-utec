# productos/urls.py
"""URLs de la app productos — W02 + W05."""
from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.index, name='inicio'),
    path('lista/',           views.ProductoListView.as_view(),   name='lista'),
    path('nuevo/',           views.ProductoCreateView.as_view(), name='crear'),
    path('<int:pk>/',        views.ProductoDetailView.as_view(), name='detalle'),
    path('<int:pk>/editar/', views.ProductoUpdateView.as_view(), name='editar'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
]