"""Pruebas de las acciones de prueba del admin (stock, venta y reporte).

Ejecutar con:
    python manage.py test tests.test_w18_acciones_admin --verbosity=2
"""
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from clientes.models      import Cliente
from configuracion.models import ConfiguracionERP
from productos.models     import Categoria, Producto
from ventas.models        import Pedido


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
    ADMINS=[('Admin Test', 'admin@test.com')],
)
class AccionesDePruebaTest(TestCase):

    def setUp(self):
        ConfiguracionERP.get_instance()
        self.admin = User.objects.create_superuser('root', 'root@test.com', 'x')
        self.client.force_login(self.admin)
        categoria = Categoria.objects.create(nombre='Cat')
        self.producto = Producto.objects.create(
            nombre='Escaso', precio=Decimal('10.00'), stock=2,
            categoria=categoria,
        )
        cliente = Cliente.objects.create(nombre='C', correo='c@test.com')
        self.pagado = Pedido.objects.create(
            numero_pedido='PED-P-1', cliente=cliente, estado='pagado',
            total_pagado=Decimal('11.60'), correo_enviado=True,
        )
        self.pendiente = Pedido.objects.create(
            numero_pedido='PED-P-2', cliente=cliente, estado='pendiente',
        )

    def _accion(self, modelo, accion, *objetos):
        return self.client.post(
            reverse(f'admin:{modelo}_changelist'),
            {'action': accion, '_selected_action': [o.pk for o in objetos]},
            follow=True,
        )

    def test_alerta_de_stock_llega_al_administrador(self):
        self._accion('productos_producto', 'probar_alerta_stock', self.producto)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@test.com'])
        self.assertIn('Escaso', mail.outbox[0].body)

    def test_sin_stock_bajo_avisa_y_no_envia(self):
        Producto.objects.update(stock=50)
        r = self._accion(
            'productos_producto', 'probar_alerta_stock', self.producto)
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(r, 'no se envía correo')

    def test_correo_de_venta_se_reenvia_solo_si_esta_pagado(self):
        self._accion('ventas_pedido', 'probar_correo_venta',
                     self.pagado, self.pendiente)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('PED-P-1', mail.outbox[0].subject)

    def test_reporte_de_hoy_se_envia(self):
        self._accion('ventas_pedido', 'enviar_reporte_hoy', self.pendiente)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reporte de ventas', mail.outbox[0].subject)
        self.assertIn('11.60', mail.outbox[0].body)

    def test_reporte_se_envia_aunque_no_haya_ventas(self):
        Pedido.objects.update(estado='pendiente')
        self._accion('ventas_pedido', 'enviar_reporte_hoy', self.pendiente)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Sin ventas registradas hoy', mail.outbox[0].body)

    def test_usuario_sin_permiso_de_edicion_no_puede_enviar(self):
        lector = User.objects.create_user('lector', password='x', is_staff=True)
        lector.user_permissions.add(
            Permission.objects.get(codename='view_pedido'))
        self.client.force_login(lector)
        self._accion('ventas_pedido', 'enviar_reporte_hoy', self.pendiente)
        self.assertEqual(len(mail.outbox), 0)
