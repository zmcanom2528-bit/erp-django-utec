import logging

import stripe
from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from productos.models import Producto
from ventas.models import Pedido

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse('Payload inválido.', status=400)
    except stripe.SignatureVerificationError:
        return HttpResponse('Firma inválida.', status=400)

    if hasattr(event, 'to_dict'):
        event = event.to_dict()

    tipo = event['type']
    if tipo == 'payment_intent.succeeded':
        _pago_exitoso(event['data']['object'])
    elif tipo == 'payment_intent.payment_failed':
        _pago_fallido(event['data']['object'])

    return HttpResponse(status=200)


def _pedido_id(payment_intent):
    valor = (payment_intent.get('metadata') or {}).get('pedido_id')
    try:
        return int(valor)
    except (TypeError, ValueError):
        logger.warning('PaymentIntent sin pedido_id en metadata.')
        return None


def _pago_exitoso(payment_intent):
    pid = _pedido_id(payment_intent)
    if pid is None:
        return
    try:
        pedido = Pedido.objects.get(pk=pid)
    except Pedido.DoesNotExist:
        logger.error(f'Pedido {pid} no existe.')
        return

    if pedido.estado != 'pagado':        # evita descontar dos veces
        pedido.estado = 'pagado'
        pedido.save(update_fields=['estado'])
        _descontar_stock(pedido)


def _pago_fallido(payment_intent):
    pid = _pedido_id(payment_intent)
    if pid is None:
        return
    Pedido.objects.filter(pk=pid, estado='pendiente').update(estado='cancelado')


def _descontar_stock(pedido):
    for item in pedido.items_snapshot or []:
        cantidad = int(item.get('cantidad', 0))
        if cantidad <= 0:
            continue
        filas = Producto.objects.filter(
            pk=item['producto_id'], stock__gte=cantidad
        ).update(stock=F('stock') - cantidad)
        if not filas:
            logger.warning(f"Stock insuficiente para producto {item['producto_id']}")