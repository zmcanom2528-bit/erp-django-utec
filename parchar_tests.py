"""Parche automático para tests/test_w08_escritura.py (permisos de W09).

Uso (desde D:\\WorkSpace_ERP):   python parchar_tests.py
Es idempotente: si ya está parchado, no hace nada.
"""
from pathlib import Path

ruta = Path('tests/test_w08_escritura.py')
txt = ruta.read_text(encoding='utf-8')

if '_dar_permisos' in txt:
    print('Ya estaba parchado. Nada que hacer.')
    raise SystemExit

HELPER = '''

def _dar_permisos(user, app_label, *codenames):
    """Asigna permisos concretos a un usuario de prueba (W09)."""
    perms = Permission.objects.filter(
        content_type__app_label=app_label,
        codename__in=codenames,
    )
    assert perms.count() == len(codenames), (
        f"Faltan permisos en {app_label}: {codenames}"
    )
    user.user_permissions.add(*perms)

'''

def reemplazar(txt, viejo, nuevo):
    if viejo not in txt:
        raise SystemExit(f'No encontré este texto en el archivo:\n{viejo}')
    return txt.replace(viejo, nuevo, 1)

txt = reemplazar(txt,
    'from django.contrib.auth.models import User',
    'from django.contrib.auth.models import Permission, User')
txt = reemplazar(txt,
    '\n\nclass ProductoEscrituraTest(TestCase):',
    HELPER + '\nclass ProductoEscrituraTest(TestCase):')
txt = reemplazar(txt,
    "            'testuser', password='testpass123'\n        )\n",
    "            'testuser', password='testpass123'\n        )\n"
    "        _dar_permisos(self.user, 'productos', 'delete_producto')\n")
txt = reemplazar(txt,
    "self.user = User.objects.create_user('userV', password='pass')\n",
    "self.user = User.objects.create_user('userV', password='pass')\n"
    "        _dar_permisos(self.user, 'ventas', 'add_venta')\n")

ruta.write_text(txt, encoding='utf-8')
print('Parche aplicado a', ruta)
