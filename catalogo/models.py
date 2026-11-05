from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class Produto(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="produtos",
    )
    nome = models.CharField(max_length=150)
    preco = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    disponivel = models.BooleanField(default=True)

    class Meta:
        ordering = ["categoria__nome", "nome"]
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nome"],
                name="produto_nome_unico_por_categoria",
            ),
            models.CheckConstraint(
                condition=models.Q(preco__gte=0),
                name="produto_preco_nao_negativo",
            ),
        ]

    def __str__(self):
        return self.nome


class AreaEntrega(models.Model):
    municipio = models.CharField(max_length=100)
    codigo_ibge = models.PositiveIntegerField(unique=True)
    taxa_entrega = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["municipio"]
        verbose_name = "área de entrega"
        verbose_name_plural = "áreas de entrega"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(taxa_entrega__gte=0),
                name="area_entrega_taxa_nao_negativa",
            ),
        ]

    def __str__(self):
        return self.municipio
