# ventas/views.py
"""Vistas de la app ventas — W02 (index) + W07 (lectura) + W08/W09 (escritura + permisos)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import DeleteView, DetailView, ListView

from .forms import DetalleVentaForm, VentaForm
from .models import Venta


def index(request):
    """Vista de índice de ventas (placeholder W02)."""
    context = {
        'titulo': 'Ventas',
        'descripcion': 'Ciclo de ventas, pedidos y facturación.',
        'espiral': 'Espiral 3 · W07',
    }
    return render(request, 'ventas/index.html', context)


class VentaListView(ListView):
    """Lista paginada de ventas en orden cronológico inverso."""

    model = Venta
    template_name = 'ventas/lista.html'
    context_object_name = 'ventas'
    paginate_by = 20

    def get_queryset(self):
        return Venta.objects.select_related('cliente').order_by('-fecha')


class VentaDetailView(DetailView):
    """Detalle de una venta con todas sus líneas de producto."""

    model = Venta
    template_name = 'ventas/detalle.html'
    context_object_name = 'venta'
    pk_url_kwarg = 'venta_id'

    def get_queryset(self):
        return (
            Venta.objects
            .select_related('cliente')
            .prefetch_related('detalles__producto')
        )


@login_required
@permission_required('ventas.add_venta', raise_exception=True)
def crear_venta(request):
    """Crea un encabezado de venta con una línea de detalle.

    @login_required            → anónimo: 302 a /accounts/login/
    @permission_required(...)  → autenticado sin permiso: 403
    """
    venta_form = VentaForm(request.POST or None)
    detalle_form = DetalleVentaForm(request.POST or None)

    if request.method == 'POST':
        if venta_form.is_valid() and detalle_form.is_valid():
            venta = venta_form.save()
            detalle = detalle_form.save(commit=False)
            detalle.venta = venta
            detalle.save()
            messages.success(
                request,
                f'Venta #{venta.pk} registrada. Total: ${venta.total:.2f}'
            )
            return redirect('ventas:detalle', venta_id=venta.pk)

    return render(request, 'ventas/crear.html', {
        'venta_form': venta_form,
        'detalle_form': detalle_form,
    })


class VentaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Borrado de una venta (requiere 'ventas.delete_venta')."""

    model = Venta
    template_name = 'ventas/eliminar.html'
    pk_url_kwarg = 'venta_id'
    success_url = reverse_lazy('ventas:lista')
    permission_required = 'ventas.delete_venta'
    raise_exception = True

    def handle_no_permission(self):
        # Sin sesión → login; con sesión pero sin permiso → 403
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path(),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())
        return super().handle_no_permission()

    def form_valid(self, form):
        pk = self.object.pk
        response = super().form_valid(form)
        messages.success(self.request, f'Venta #{pk} eliminada.')
        return response
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from configuracion.models import ConfiguracionERP
from .models import Venta


@login_required
def venta_pdf(request, venta_id: int) -> HttpResponse:
    """Genera y descarga la factura en PDF de una venta usando xhtml2pdf."""
    venta = get_object_or_404(
        Venta.objects
        .select_related('cliente')
        .prefetch_related('detalles__producto'),
        pk=venta_id
    )

    config = ConfiguracionERP.get_instance()
    context = {
        'venta': venta,
        'config': config,
    }

    html_string = render_to_string('ventas/factura_pdf.html', context, request=request)

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(src=html_string, dest=buffer)

    if pisa_status.err:
        return HttpResponse('Error al generar el PDF de la factura', status=500)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_{venta.pk:05d}.pdf"'
    return response

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from openpyxl import Workbook
from .models import Producto

@login_required
def exportar_excel(request) -> HttpResponse:
    """Genera y descarga un archivo Excel con el inventario de productos."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    ws.append(["ID", "Nombre", "Precio", "Stock", "Categoría"])

    for prod in Producto.objects.select_related('categoria').all():
        ws.append([
            prod.pk,
            prod.nombre,
            float(prod.precio),
            prod.stock,
            prod.categoria.nombre if prod.categoria else "Sin categoría"
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="inventario_productos.xlsx"'
    wb.save(response)
    return response

