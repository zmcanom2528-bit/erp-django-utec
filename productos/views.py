# productos/views.py
"""Vistas de la app productos — W02 + CRUD W05 + imagen W11 + auth/permisos W08-W09."""

from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from openpyxl import Workbook

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


class LoginOr403Mixin(LoginRequiredMixin):
    """Sin sesión → 302 al login. Con sesión pero sin permiso → 403."""

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        raise PermissionDenied


class ProductoListView(ListView):
    model = Producto
    template_name = 'productos/lista.html'
    context_object_name = 'productos'
    paginate_by = 20
    ordering = ['pk']


class ProductoDetailView(DetailView):
    model = Producto
    template_name = 'productos/detalle.html'


class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm          # W11: formulario con imagen
    template_name = 'productos/crear.html'
    success_url = reverse_lazy('productos:lista')


class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model = Producto
    form_class = ProductoForm          # W11: formulario con imagen
    template_name = 'productos/form.html'
    success_url = reverse_lazy('productos:lista')


class ProductoDeleteView(LoginOr403Mixin, PermissionRequiredMixin, DeleteView):
    model = Producto
    template_name = 'productos/confirmar_eliminar.html'
    success_url = reverse_lazy('productos:lista')
    permission_required = 'productos.delete_producto'
    raise_exception = True


@login_required
def exportar_excel(request) -> HttpResponse:
    """Genera y descarga un archivo Excel con el inventario de productos."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Productos'

    # Columnas = todos los campos del modelo, menos archivos/imágenes
    campos = [
        f for f in Producto._meta.fields
        if f.get_internal_type() not in ('FileField', 'ImageField')
    ]
    ws.append([str(f.verbose_name).capitalize() for f in campos])

    for producto in Producto.objects.all().order_by('pk'):
        fila = []
        for f in campos:
            valor = getattr(producto, f.name)
            if isinstance(valor, datetime) and valor.tzinfo is not None:
                valor = valor.replace(tzinfo=None)
            elif valor is not None and not isinstance(valor, (int, float, bool, str, datetime)):
                valor = str(valor)
            fila.append(valor)
        ws.append(fila)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="productos.xlsx"'
    wb.save(response)
    return response