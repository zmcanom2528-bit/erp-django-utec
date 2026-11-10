# productos/views.py
"""Vistas de la app productos — W02 + CRUD de W05."""
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView

from .models import Producto


def index(request):
    """Vista de índice de productos.

    Returns:
        HttpResponse con template productos/index.html.
    """
    context = {
        'titulo': 'Productos',
        'descripcion': 'Gestión de inventario y catálogo de productos.',
        'espiral': 'Espiral 2 · W05',
    }
    return render(request, 'productos/index.html', context)


class ProductoListView(ListView):
    model = Producto
    template_name = 'productos/lista.html'
    context_object_name = 'productos'


class ProductoDetailView(DetailView):
    model = Producto
    template_name = 'productos/detalle.html'


class ProductoCreateView(CreateView):
    model = Producto
    fields = '__all__'
    template_name = 'productos/form.html'
    success_url = reverse_lazy('productos:lista')


class ProductoUpdateView(UpdateView):
    model = Producto
    fields = '__all__'
    template_name = 'productos/form.html'
    success_url = reverse_lazy('productos:lista')