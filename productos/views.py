# productos/views.py
"""Vistas de la app productos — W02 + CRUD de W05 + imagen W11."""

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from openpyxl import Workbook


from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView

from .forms import ProductoForm
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
    form_class = ProductoForm          # W11: usa el formulario con imagen
    template_name = 'productos/form.html'
    success_url = reverse_lazy('productos:lista')


class ProductoUpdateView(UpdateView):
    model = Producto
    form_class = ProductoForm          # W11: usa el formulario con imagen
    template_name = 'productos/form.html'
    success_url = reverse_lazy('productos:lista')

    success_url = reverse_lazy('productos:lista')

@login_required
def exportar_excel(request) -> HttpResponse:
    """Genera y descarga un archivo Excel con el inventario de productos."""
    wb = Workbook()

    # ... (código donde creas el archivo y llenas las celdas) ...
    
    # Preparar la respuesta HTTP para descargar el archivo
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="productos.xlsx"'
    
    # Guardar el libro de trabajo en la respuesta
    wb.save(response)
    
    # Retornar la respuesta (¡Esta es la línea que te falta!)
    return response