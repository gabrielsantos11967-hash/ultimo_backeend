from django.contrib import admin, messages
from django.db.models import Count
from django.forms.models import BaseInlineFormSet

from .models import (
    TAXA_ENTREGA_PADRAO,
    AreaEntrega,
    Categoria,
    Nome,
    Pedido,
    PedidoItem,
    Produto,
)


class ProdutoInline(admin.TabularInline):
    model = Produto
    extra = 1
    fields = ("nome", "preco", "disponivel")


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "quantidade_produtos", "ativa")
    list_editable = ("ativa",)
    list_filter = ("ativa",)
    search_fields = ("nome", "descricao")
    inlines = (ProdutoInline,)
    ordering = ("nome",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            total_produtos=Count("produtos")
        )

    @admin.display(description="Produtos", ordering="total_produtos")
    def quantidade_produtos(self, obj):
        return obj.total_produtos


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco", "categoria", "disponivel")
    list_editable = ("disponivel",)
    list_filter = ("categoria", "disponivel")
    search_fields = ("nome",)
    list_select_related = ("categoria",)
    autocomplete_fields = ("categoria",)
    ordering = ("categoria__nome", "nome")
    actions = ("marcar_indisponiveis",)

    @admin.action(description="Marcar como indisponível")
    def marcar_indisponiveis(self, request, queryset):
        atualizados = queryset.update(disponivel=False)
        self.message_user(
            request,
            f"{atualizados} produto(s) marcado(s) como indisponível.",
            messages.SUCCESS,
        )


@admin.register(AreaEntrega)
class AreaEntregaAdmin(admin.ModelAdmin):
    list_display = ("municipio", "codigo_ibge", "taxa_entrega")
    search_fields = ("municipio", "codigo_ibge")
    ordering = ("municipio",)


@admin.register(Nome)
class NomeAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)


class PedidoItemInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        form.instance.preco_unitario = form.instance.produto.preco
        return super().save_new(form, commit=commit)


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    autocomplete_fields = ("produto",)
    readonly_fields = ("preco_unitario",)
    formset = PedidoItemInlineFormSet


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente_nome",
        "municipio",
        "status",
        "total",
        "criado_em",
    )
    list_filter = ("status", "area_entrega", "criado_em")
    search_fields = ("cliente_nome", "telefone")
    list_select_related = ("area_entrega", "usuario")
    readonly_fields = ("taxa_entrega", "criado_em", "atualizado_em")
    inlines = (PedidoItemInline,)
    autocomplete_fields = ("usuario", "area_entrega")
    ordering = ("-criado_em",)

    @admin.display(description="Município", ordering="area_entrega__municipio")
    def municipio(self, obj):
        return obj.area_entrega.municipio

    def save_model(self, request, obj, form, change):
        if not change:
            obj.taxa_entrega = TAXA_ENTREGA_PADRAO
        super().save_model(request, obj, form, change)


admin.site.site_header = "Administração da Lanchonete"
admin.site.site_title = "Lanchonete | Administração"
admin.site.index_title = "Gerenciamento do cardápio"
