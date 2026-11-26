"""Suite de pruebas W14 — Checkout y proceso de pago con Stripe.

Usa unittest.mock.patch para simular stripe.PaymentIntent.create
y la confirmación del pago, sin requerir claves reales ni internet.

Ejecutar con:
    python manage.py test tests.test_w14_checkout --verbosity=2
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogo.checkout_utils import obtener_o_crear_cliente
from clientes.models        import Cliente
from configuracion.models   import ConfiguracionERP
from productos.models       import Categoria, Producto
from ventas.models          import Pedido


def _setup_carrito(client, producto):
    """Agrega un producto al carrito de la sesión del test client."""
    client.post(
        reverse('catalogo:agregar', args=[producto.pk]),
        {'cantidad': 2}
    )


def _intent_falso():
    """PaymentIntent simulado: id y client_secret deben ser strings reales."""
    return MagicMock(id='pi_test_123', client_secret='pi_test_secret')


class CheckoutAutenticacionTest(TestCase):
    """Tests de autenticación del checkout."""

    def test_checkout_sin_auth_redirige_a_login(self):
        """GET /catalogo/checkout/ sin login → 302 a /accounts/login/."""
        r = self.client.get(reverse('catalogo:checkout'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r['Location'])

    def test_checkout_carrito_vacio_redirige_a_catalogo(self):
        """Checkout con carrito vacío → redirect al catálogo."""
        user = User.objects.create_user('empty', password='pass')
        self.client.force_login(user)
        r = self.client.get(reverse('catalogo:checkout'))
        self.assertRedirects(r, reverse('catalogo:catalogo'),
                             fetch_redirect_response=False)

    def test_checkout_get_con_carrito_devuelve_200(self):
        """GET /catalogo/checkout/ con carrito → 200 (resumen visible)."""
        ConfiguracionERP.get_instance()
        cat  = Categoria.objects.create(nombre='Cat')
        prod = Producto.objects.create(
            nombre='P', precio=Decimal('100.00'),
            stock=5, categoria=cat
        )
        user = User.objects.create_user('userco', password='pass',
                                        email='userco@test.com')
        self.client.force_login(user)
        _setup_carrito(self.client, prod)
        r = self.client.get(reverse('catalogo:checkout'))
        self.assertEqual(r.status_code, 200)


class CheckoutPagoTest(TestCase):
    """Tests del proceso POST de checkout con Stripe mockeado."""

    def setUp(self):
        ConfiguracionERP.get_instance()
        cat       = Categoria.objects.create(nombre='Cat')
        self.prod = Producto.objects.create(
            nombre='Laptop', precio=Decimal('500.00'),
            stock=5, categoria=cat
        )
        self.user = User.objects.create_user(
            'payer', password='pass', email='payer@test.com'
        )
        self.client.force_login(self.user)
        _setup_carrito(self.client, self.prod)   # 2 × 500 = 1000

    @patch('catalogo.views.stripe.PaymentIntent.create')
    def test_post_checkout_crea_pedido(self, mock_pi):
        """POST /catalogo/checkout/ → se crea un Pedido en BD."""
        mock_pi.return_value = _intent_falso()
        self.client.post(reverse('catalogo:checkout'))
        self.assertEqual(Pedido.objects.count(), 1)

    @patch('catalogo.views.stripe.PaymentIntent.create')
    def test_post_checkout_pedido_estado_pendiente(self, mock_pi):
        """El Pedido creado debe tener estado 'pendiente'."""
        mock_pi.return_value = _intent_falso()
        self.client.post(reverse('catalogo:checkout'))
        pedido = Pedido.objects.first()
        self.assertEqual(pedido.estado, 'pendiente')

    @patch('catalogo.views.stripe.PaymentIntent.create')
    def test_post_checkout_guarda_payment_intent(self, mock_pi):
        """El id del PaymentIntent queda guardado en el Pedido."""
        mock_pi.return_value = _intent_falso()
        self.client.post(reverse('catalogo:checkout'))
        pedido = Pedido.objects.first()
        self.assertEqual(pedido.stripe_payment_intent, 'pi_test_123')

    @patch('catalogo.views.stripe.PaymentIntent.create')
    def test_post_checkout_calcula_iva(self, mock_pi):
        """El total del Pedido debe incluir el IVA configurado."""
        mock_pi.return_value = _intent_falso()
        self.client.post(reverse('catalogo:checkout'))
        pedido    = Pedido.objects.first()
        config    = ConfiguracionERP.get_instance()
        subtotal  = Decimal('1000.00')   # 2 × 500
        iva_pct   = config.iva_porcentaje / 100
        esperado  = (subtotal + subtotal * iva_pct).quantize(Decimal('0.01'))
        self.assertEqual(pedido.total_pagado, esperado)

    @patch('catalogo.views.stripe.PaymentIntent.create')
    def test_post_checkout_crea_cliente_erp(self, mock_pi):
        """Se debe crear (o encontrar) un Cliente ERP para el usuario."""
        mock_pi.return_value = _intent_falso()
        self.client.post(reverse('catalogo:checkout'))
        self.assertTrue(
            Cliente.objects.filter(correo=self.user.email).exists()
        )

    @patch('catalogo.views.stripe.PaymentIntent.create')
    def test_post_checkout_llama_stripe_con_monto_correcto(self, mock_pi):
        """Stripe debe recibir el monto en centavos."""
        mock_pi.return_value = _intent_falso()
        self.client.post(reverse('catalogo:checkout'))
        config   = ConfiguracionERP.get_instance()
        subtotal = Decimal('1000.00')
        total    = subtotal + subtotal * (config.iva_porcentaje / 100)
        centavos = int(total.quantize(Decimal('0.01')) * 100)
        mock_pi.assert_called_once()
        args, kwargs = mock_pi.call_args
        self.assertEqual(kwargs.get('amount') or args[0], centavos)


class PagoExitosoTest(TestCase):
    """Tests de la vista pago_exitoso (con la confirmación de Stripe mockeada)."""

    def setUp(self):
        ConfiguracionERP.get_instance()
        cat = Categoria.objects.create(nombre='C')
        self.prod = Producto.objects.create(
            nombre='P', precio=Decimal('100.00'), stock=5, categoria=cat
        )
        self.user = User.objects.create_user(
            'comprador', password='pass', email='comprador@test.com'
        )
        self.client.force_login(self.user)

        # El Cliente ERP debe ser el mismo que la vista asocia a este usuario
        cli = obtener_o_crear_cliente(self.user)
        self.pedido = Pedido.objects.create(
            numero_pedido='PED-2025-0001',
            cliente=cli,
            estado='pendiente',
            total_pagado=Decimal('116.00'),
            stripe_payment_intent='pi_test_123',
            items_snapshot=[{
                'producto_id': self.prod.pk,
                'nombre':      'P',
                'cantidad':    2,
                'precio':      '100.00',
            }],
        )

    def _url(self):
        return reverse('catalogo:pago_exitoso', args=[self.pedido.pk])

    @patch('catalogo.views._pago_confirmado', return_value=True)
    def test_pago_exitoso_devuelve_200(self, _mock):
        """GET /catalogo/pago-exitoso/<id>/ → 200."""
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 200)

    @patch('catalogo.views._pago_confirmado', return_value=True)
    def test_pago_exitoso_vacia_carrito(self, _mock):
        """Visitar pago_exitoso vacía la sesión del carrito."""
        session = self.client.session
        session['carrito'] = {'1': {'nombre': 'P', 'precio': '100',
                                     'cantidad': 1}}
        session.save()

        self.client.get(self._url())
        self.assertEqual(self.client.session.get('carrito', {}), {})

    @patch('catalogo.views._pago_confirmado', return_value=True)
    def test_pago_exitoso_marca_pagado_y_descuenta_stock(self, _mock):
        """Con pago confirmado: pedido 'pagado' y stock descontado."""
        self.client.get(self._url())
        self.pedido.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'pagado')
        self.assertEqual(self.prod.stock, 3)   # 5 - 2

    @patch('catalogo.views._pago_confirmado', return_value=True)
    def test_pago_exitoso_recarga_no_descuenta_dos_veces(self, _mock):
        """Recargar la página no vuelve a descontar el stock."""
        self.client.get(self._url())
        self.client.get(self._url())
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock, 3)

    @patch('catalogo.views._pago_confirmado', return_value=False)
    def test_pago_no_confirmado_redirige_a_error(self, _mock):
        """Si Stripe no confirma: redirect a pago_error y pedido pendiente."""
        r = self.client.get(self._url())
        self.assertRedirects(r, reverse('catalogo:pago_error'),
                             fetch_redirect_response=False)
        self.pedido.refresh_from_db()
        self.prod.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'pendiente')
        self.assertEqual(self.prod.stock, 5)

    @patch('catalogo.views._pago_confirmado', return_value=True)
    def test_pedido_de_otro_usuario_da_404(self, _mock):
        """Un usuario no puede ver el pedido de otra persona."""
        otro = User.objects.create_user(
            'otro', password='pass', email='otro@test.com'
        )
        self.client.force_login(otro)
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 404)