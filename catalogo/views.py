# catalogo/views.py
"""Vistas del módulo de catálogo, carrito y checkout — W13/W14/W15.

El carrito se almacena en la sesión Django.

Estructura del carrito en sesión:
    request.session['carrito'] = {
        '1': {
            'nombre':   'Laptop HP',
            'precio':   '10000.00',   # str — Decimal no es JSON serializable
            'cantidad': 2,
            'imagen':   'productos/laptop.jpg'  # o None
        },
        ...
    }
"""
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, IntegerField, Value
from django.db.models.functions import Greatest
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from productos.models import Producto
from ventas.models import DetalleVenta, Pedido

from .checkout_utils import (
    calcular_totales,
    obtener_o_crear_cliente,
)
from .filters import ProductoFilter

# Configurar la clave secreta de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# ── CATÁLOGO ───────────────────────────────────────────────────────────────

class CatalogoView(ListView):
    """Catálogo público de productos con filtros.

    No requiere autenticación — accesible para cualquier visitante.
    """

    model               = Producto
    template_name       = 'catalogo/catalogo.html'
    context_object_name = 'productos'
    paginate_by         = 12    # 3 filas de 4 tarjetas

    def get_queryset(self):
        """Filtra productos activos aplicando los filtros del request."""
        qs = (
            Producto.objects
            .select_related('categoria', 'proveedor')
            .filter(activo=True)
            .order_by('nombre')
        )
        self.filtro = ProductoFilter(self.request.GET, queryset=qs)
        return self.filtro.qs

    def get_context_data(self, **kwargs):
        """Agrega el objeto filtro al contexto para renderizar el formulario."""
        ctx = super().get_context_data(**kwargs)
        ctx['filtro']     = self.filtro
        ctx['categorias'] = self.filtro.form.fields['categoria'].queryset
        return ctx


# ── CARRITO ─────────────────────────────────────────────────────────────────

def _obtener_carrito(request) -> dict:
    """Obtiene el carrito de la sesión o crea uno vacío."""
    return request.session.get('carrito', {})


def _guardar_carrito(request, carrito: dict) -> None:
    """Guarda el carrito en la sesión y marca como modificado."""
    request.session['carrito'] = carrito
    request.session.modified   = True


def ver_carrito(request):
    """Muestra el contenido del carrito con el total calculado.

    Convierte los precios de str a Decimal para el cálculo.
    """
    carrito = _obtener_carrito(request)

    items = []
    total = Decimal('0.00')

    for prod_id, datos in carrito.items():
        precio   = Decimal(datos['precio'])
        cantidad = int(datos['cantidad'])
        subtotal = precio * cantidad
        total   += subtotal
        items.append({
            'prod_id':  prod_id,
            'nombre':   datos['nombre'],
            'precio':   precio,
            'cantidad': cantidad,
            'subtotal': subtotal,
            'imagen':   datos.get('imagen'),
        })

    return render(request, 'catalogo/carrito.html', {
        'items': items,
        'total': total,
    })


def agregar_al_carrito(request, producto_id: int):
    """Agrega un producto al carrito o incrementa su cantidad.

    Solo acepta POST para proteger contra CSRF.
    La cantidad puede enviarse como parámetro POST (default: 1).

    Args:
        producto_id: ID del producto a agregar.
    """
    if request.method != 'POST':
        return redirect('catalogo:catalogo')

    producto = get_object_or_404(Producto, pk=producto_id, activo=True)
    carrito  = _obtener_carrito(request)

    clave    = str(producto_id)
    cantidad = int(request.POST.get('cantidad', 1))

    if clave in carrito:
        carrito[clave]['cantidad'] += cantidad
    else:
        carrito[clave] = {
            'nombre':   producto.nombre,
            'precio':   str(producto.precio),   # str para JSON serializable
            'cantidad': cantidad,
            'imagen':   producto.imagen.name if producto.imagen else None,
        }

    _guardar_carrito(request, carrito)
    messages.success(
        request,
        f'"{producto.nombre}" agregado al carrito.'
    )

    # Volver a la página anterior (catálogo, detalle de producto, etc.)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'catalogo:catalogo')


def remover_del_carrito(request, producto_id: int):
    """Elimina un producto del carrito.

    Solo acepta POST.
    """
    if request.method != 'POST':
        return redirect('catalogo:carrito')

    carrito = _obtener_carrito(request)
    clave   = str(producto_id)

    nombre = carrito.get(clave, {}).get('nombre', 'Producto')
    carrito.pop(clave, None)
    _guardar_carrito(request, carrito)

    messages.warning(request, f'"{nombre}" eliminado del carrito.')
    return redirect('catalogo:carrito')


def actualizar_cantidad(request, producto_id: int):
    """Actualiza la cantidad de un producto en el carrito.

    Solo acepta POST. Si la cantidad llega a 0 o menos, elimina el item.
    """
    if request.method != 'POST':
        return redirect('catalogo:carrito')

    carrito  = _obtener_carrito(request)
    clave    = str(producto_id)
    cantidad = int(request.POST.get('cantidad', 1))

    if clave in carrito:
        if cantidad > 0:
            carrito[clave]['cantidad'] = cantidad
        else:
            carrito.pop(clave)

    _guardar_carrito(request, carrito)
    return redirect('catalogo:carrito')


def vaciar_carrito(request):
    """Elimina todos los productos del carrito."""
    if request.method == 'POST':
        _guardar_carrito(request, {})
        messages.info(request, 'Carrito vaciado.')
    return redirect('catalogo:carrito')


# ── STOCK ───────────────────────────────────────────────────────────────────

def _stock_insuficiente(carrito: dict) -> list:
    """Revisa que haya existencias para todo lo que está en el carrito.

    Returns:
        Lista de textos con los productos que no alcanzan (vacía si todo ok).
    """
    productos = Producto.objects.in_bulk([int(pk) for pk in carrito])
    problemas = []
    for prod_id, datos in carrito.items():
        producto = productos.get(int(prod_id))
        cantidad = int(datos['cantidad'])
        if producto is None:
            problemas.append(f'"{datos["nombre"]}" ya no está disponible')
        elif producto.stock < cantidad:
            problemas.append(
                f'"{producto.nombre}": pediste {cantidad} y solo quedan '
                f'{producto.stock}'
            )
    return problemas


def _descontar_stock(items: list) -> None:
    """Resta del inventario las cantidades de un pedido.

    Usa F() para que la resta la haga la base de datos (segura aunque dos
    compras ocurran al mismo tiempo) y Greatest() para que nunca quede
    negativo.

    Args:
        items: lista de dicts con 'producto_id' y 'cantidad'
               (el items_snapshot del Pedido).
    """
    for item in items:
        Producto.objects.filter(pk=item['producto_id']).update(
            stock=Greatest(
                F('stock') - int(item['cantidad']),
                Value(0),
                output_field=IntegerField(),
            )
        )


def _pago_confirmado(pedido) -> bool:
    """Pregunta a Stripe si el cobro de este pedido realmente se completó.

    No basta con que el navegador llegue a la URL de éxito: se consulta el
    PaymentIntent guardado y se comprueba que esté 'succeeded' y que el
    monto y la moneda coincidan con el pedido.

    Returns:
        True solo si Stripe confirma el pago completo.
    """
    if not pedido.stripe_payment_intent or pedido.total_pagado is None:
        return False
    try:
        intent = stripe.PaymentIntent.retrieve(pedido.stripe_payment_intent)
    except stripe.StripeError:
        return False

    monto_esperado = int(pedido.total_pagado * 100)
    return (
        intent.status == 'succeeded'
        and intent.amount == monto_esperado
        and intent.currency == 'mxn'
    )


# ── CHECKOUT (W14 + W15) ────────────────────────────────────────────────────

@login_required
def checkout(request):
    """Proceso de pago: muestra resumen y crea PaymentIntent de Stripe.

    GET:  Muestra resumen del carrito con IVA calculado.
          No crea PaymentIntent (espera a POST).

    POST: Valida carrito y stock → crea Pedido (con snapshot de items) →
          crea PaymentIntent → retorna client_secret al template para
          que Stripe.js confirme el pago del lado del cliente.

    El stock se descuenta en pago_exitoso, cuando el pago ya se confirmó.

    Redirige a /catalogo/ si el carrito está vacío.
    """
    carrito = _obtener_carrito(request)
    if not carrito:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('catalogo:catalogo')

    totales         = calcular_totales(carrito)
    publishable_key = settings.STRIPE_PUBLISHABLE_KEY

    if request.method == 'POST':
        try:
            # ── 0. Verificar que haya existencias ──────────────────────
            problemas = _stock_insuficiente(carrito)
            if problemas:
                for texto in problemas:
                    messages.error(request, texto)
                return redirect('catalogo:carrito')

            # ── 1. Vincular usuario con Cliente del ERP ────────────────
            cliente = obtener_o_crear_cliente(request.user)

            # ── 2. Crear el Pedido con snapshot del carrito ────────────
            # numero_pedido no se manda: Pedido.save() genera uno único.
            snapshot = [
                {
                    'producto_id': int(prod_id),
                    'nombre':      datos['nombre'],
                    'cantidad':    int(datos['cantidad']),
                    'precio':      datos['precio'],
                }
                for prod_id, datos in carrito.items()
            ]

            pedido = Pedido.objects.create(
                cliente        = cliente,
                estado         = 'pendiente',
                total_pagado   = totales['total'],
                items_snapshot = snapshot,
            )

            # ── 3. Crear PaymentIntent en Stripe ───────────────────────
            # Monto en centavos (Stripe requiere entero)
            monto_centavos = int(totales['total'] * 100)

            intent = stripe.PaymentIntent.create(
                amount          = monto_centavos,
                currency        = 'mxn',
                metadata        = {
                    'pedido_id':  pedido.pk,
                    'pedido_num': pedido.numero_pedido,
                    'cliente':    cliente.nombre,
                },
                idempotency_key = f'pedido-{pedido.pk}',
            )

            # Guardar el id del cobro para verificarlo después con Stripe
            pedido.stripe_payment_intent = intent.id
            pedido.save(update_fields=['stripe_payment_intent'])

            # ── 4. Retornar client_secret al template ──────────────────
            return render(request, 'catalogo/checkout.html', {
                'carrito':         carrito,
                'totales':         totales,
                'pedido':          pedido,
                'client_secret':   intent.client_secret,
                'publishable_key': publishable_key,
            })

        except stripe.StripeError as exc:
            messages.error(
                request,
                f'Error al conectar con Stripe: {exc.user_message}'
            )
            return redirect('catalogo:pago_error')

        except Exception as exc:
            messages.error(
                request,
                f'Error inesperado en el proceso de pago: {exc}'
            )
            return redirect('catalogo:pago_error')

    # GET — solo mostrar resumen (sin PaymentIntent)
    return render(request, 'catalogo/checkout.html', {
        'carrito':         carrito,
        'totales':         totales,
        'client_secret':   None,          # se genera en POST
        'publishable_key': publishable_key,
    })


@login_required
def pago_exitoso(request, pedido_id: int):
    """Vista de confirmación post-pago exitoso.

    Verifica con Stripe que el cobro se completó, y solo entonces marca el
    pedido como pagado, descuenta el stock y vacía el carrito.

    W16: esta vista NO encola la tarea de correo. La encola el webhook
    (catalogo/webhook_views.py), que Stripe envía aunque el cliente cierre
    el navegador.

    Seguridad:
        - Requiere iniciar sesión.
        - Solo el dueño del pedido (o personal del ERP) puede verlo.
        - Si Stripe no confirma el pago, el pedido sigue 'pendiente'.
        - Es segura ante recargas: el stock solo se descuenta mientras el
          pedido no está pagado; después ya queda 'pagado'.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    # Un cliente no puede ver (ni confirmar) pedidos de otras personas
    if not request.user.is_staff:
        if pedido.cliente != obtener_o_crear_cliente(request.user):
            raise Http404

    # 'cancelado' entra aquí porque un intento fallido cancela el pedido y el
    # cliente puede reintentar el mismo cobro: solo Stripe decide si se pagó.
    sin_pagar = ('pendiente', 'cancelado')

    if pedido.estado in sin_pagar:
        # Consulta a Stripe fuera de la transacción (es una llamada de red)
        if not _pago_confirmado(pedido):
            messages.error(
                request,
                'No pudimos confirmar tu pago con Stripe. Si se te cobró, '
                f'guarda tu número de pedido ({pedido.numero_pedido}) '
                'y contáctanos.'
            )
            return redirect('catalogo:pago_error')

        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
            if pedido.estado in sin_pagar:
                _descontar_stock(pedido.items_snapshot)
                pedido.estado = 'pagado'
                pedido.save(update_fields=['estado'])

    # Vaciar el carrito al confirmar el pago
    _guardar_carrito(request, {})
    messages.success(
        request,
        f'¡Pago exitoso! Tu pedido {pedido.numero_pedido} '
        f'está confirmado. Total: ${pedido.total_pagado}. '
        f'Recibirás un correo de confirmación pronto.'
    )

    return render(request, 'catalogo/pago_exitoso.html', {
        'pedido': pedido,
    })


def pago_error(request):
    """Vista de error de pago — muestra mensaje y permite reintentar."""
    return render(request, 'catalogo/pago_error.html')
