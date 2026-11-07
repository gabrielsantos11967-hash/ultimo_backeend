from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


TAXA_ENTREGA_PADRAO = Decimal("10.00")


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


class Nome(models.Model):
    nome = models.CharField(max_length=150)

    class Meta:
        ordering = ["nome"]
        verbose_name = "nome"
        verbose_name_plural = "nomes"

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_PREPARO = "em_preparo", "Em preparo"
        SAIU_PARA_ENTREGA = "saiu_para_entrega", "Saiu para entrega"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    cliente_nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=30)
    endereco = models.CharField(max_length=255)
    area_entrega = models.ForeignKey(
        AreaEntrega,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    taxa_entrega = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    @property
    def total(self):
        return sum(
            (item.subtotal for item in self.itens.all()),
            self.taxa_entrega,
        )

    def __str__(self):
        return f"Pedido #{self.pk} - {self.cliente_nome}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name="itens_pedido",
    )
    quantidade = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["id"]
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"
        constraints = [
            models.UniqueConstraint(
                fields=["pedido", "produto"],
                name="pedido_produto_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=1),
                name="pedido_item_quantidade_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(preco_unitario__gte=0),
                name="pedido_item_preco_nao_negativo",
            ),
        ]

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade

    def __str__(self):
        return f"{self.quantidade} x {self.produto.nome}"
