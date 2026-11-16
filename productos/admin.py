# productos/admin.py
"""Configuración del panel admin para la app productos — Espiral 4 W11."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Admin de categorías."""

    list_display  = ['pk', 'nombre', 'descripcion']
    search_fields = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Admin de productos: lista con categoría, proveedor, stock e imagen."""

    list_display    = ['pk', 'miniatura', 'nombre', 'precio', 'stock',
                       'categoria', 'proveedor', 'activo', 'creado']
    search_fields   = ['nombre', 'categoria__nombre', 'proveedor__nombre']
    list_filter     = ['activo', 'categoria']
    list_editable   = ['precio', 'stock', 'activo']
    readonly_fields = ['creado', 'vista_previa']
    autocomplete_fields = ['proveedor']
    date_hierarchy  = 'creado'
    ordering        = ['nombre']

    @admin.display(description='Img')
    def miniatura(self, obj: Producto) -> str:
        """Miniatura de la imagen en la lista, si existe."""
        if obj.imagen:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;'
                'object-fit:cover;border-radius:6px;">',
                obj.imagen.url
            )
        return '—'

    @admin.display(description='Vista previa')
    def vista_previa(self, obj: Producto) -> str:
        """Vista previa grande dentro del formulario de edición."""
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-width:220px;border-radius:10px;">',
                obj.imagen.url
            )
        return 'Sin imagen'