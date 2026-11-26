import logging

import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from productos.models import Producto
from ventas.models import Pedido
from ventas.tasks import enviar_confirmacion_pedido   # W16

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
    # select_for_update: la vista pago_exitoso y el webhook pueden llegar a la
    # vez; el bloqueo evita que ambos descuenten el stock.
    with transaction.atomic():
        try:
            pedido = Pedido.objects.select_for_update().get(pk=pid)
        except Pedido.DoesNotExist:
            logger.error(f'Pedido {pid} no existe.')
            return

        if pedido.estado in ('pendiente', 'cancelado'):
            pedido.estado = 'pagado'
            pedido.save(update_fields=['estado'])
            _descontar_stock(pedido)
        else:
            logger.info(
                f'Pedido {pedido.numero_pedido} ya estaba pagado — '
                f'idempotente, sin cambios de estado ni de stock.'
            )

    # ── W16: encolar la tarea de confirmación ─────────────────────────────
    # El webhook es el ÚNICO punto que dispara el correo. Se encola aunque
    # pago_exitoso() haya marcado el pedido antes (si no, ese cliente se
    # quedaría sin correo). La tarea evita duplicados (W17: correo_enviado).
    # Si Redis no responde, el pago ya quedó registrado: se deja constancia
    # en el log y se responde 200 a Stripe igualmente.
    if pedido.estado == 'pagado':
        try:
            enviar_confirmacion_pedido.delay(pedido.pk)
        except Exception:
            logger.exception(
                f'Webhook: no se pudo encolar la confirmación del '
                f'pedido {pedido.numero_pedido} (¿Redis disponible?).'
            )


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