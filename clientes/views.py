# clientes/views.py
"""Vistas de la app clientes — W07.

Lectura: ListView y DetailView.
Escritura (Create/Update/Delete): W08.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from .forms import ClienteForm

from .models import Cliente


class ClienteListView(ListView):
    """Lista paginada de clientes activos."""

    model               = Cliente
    template_name       = 'clientes/lista.html'
    context_object_name = 'clientes'
    paginate_by         = 20

    def get_queryset(self):
        return Cliente.objects.filter(activo=True).order_by('nombre')


class ClienteDetailView(DetailView):
    """Detalle de un cliente con su historial de ventas."""

    model               = Cliente
    template_name       = 'clientes/detalle.html'
    context_object_name = 'cliente'
    pk_url_kwarg        = 'cliente_id'

    def get_context_data(self, **kwargs):
        """Agrega las ventas del cliente al contexto."""
        ctx = super().get_context_data(**kwargs)
        ctx['ventas'] = (
            self.object.ventas
            .order_by('-fecha')[:10]   # últimas 10 ventas
        )
        return ctx


class ClienteCreateView(LoginRequiredMixin, CreateView):
    """Formulario para crear un nuevo cliente."""

    model         = Cliente
    form_class    = ClienteForm
    template_name = 'clientes/crear.html'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Cliente "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    """Formulario para editar un cliente."""

    model         = Cliente
    form_class    = ClienteForm
    template_name = 'clientes/editar.html'
    pk_url_kwarg  = 'cliente_id'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Cliente "{self.object.nombre}" actualizado.'
        )
        return response


class ClienteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model               = Cliente
    template_name       = 'clientes/eliminar.html'
    pk_url_kwarg        = 'cliente_id'
    success_url         = reverse_lazy('clientes:lista')
    permission_required = 'clientes.delete_cliente'
    raise_exception     = True

    def handle_no_permission(self):
        # Sin sesión → login; con sesión pero sin permiso → 403
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path(),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())
        return super().handle_no_permission()

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Cliente "{nombre}" eliminado.')
        return response

