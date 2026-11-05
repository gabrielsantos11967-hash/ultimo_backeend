from django.contrib import admin, messages
from django.db.models import Count

from .models import AreaEntrega, Categoria, Produto


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


admin.site.site_header = "Administração da Lanchonete"
admin.site.site_title = "Lanchonete | Administração"
admin.site.index_title = "Gerenciamento do cardápio"
