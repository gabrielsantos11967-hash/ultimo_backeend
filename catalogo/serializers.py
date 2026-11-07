from rest_framework import serializers

from rest_framework.exceptions import APIException
from rest_framework.authtoken.serializers import AuthTokenSerializer
from django.db import transaction

from .ibge import (
    IBGEInvalidResponse,
    IBGEUnavailable,
    codigo_municipio_existe,
)
from .models import AreaEntrega, Categoria, Nome, Pedido, PedidoItem, Produto


class ApiTokenSerializer(AuthTokenSerializer):
    pass


class IBGEUnavailableAPIException(APIException):
    status_code = 503
    default_detail = "O IBGE está indisponível. Tente novamente."
    default_code = "ibge_unavailable"


class IBGEInvalidResponseAPIException(APIException):
    status_code = 502
    default_detail = "O IBGE retornou uma resposta inválida."
    default_code = "ibge_invalid_response"


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nome", "descricao", "ativa"]
        read_only_fields = ["id"]


class ProdutoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        source="categoria",
        queryset=Categoria.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Produto
        fields = [
            "id",
            "nome",
            "preco",
            "disponivel",
            "categoria_nome",
            "categoria_id",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "preco": {"validators": []},
        }

    def validate_preco(self, value):
        if value < 0:
            raise serializers.ValidationError("O preço não pode ser negativo.")
        return value


class AreaEntregaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaEntrega
        fields = ["id", "municipio", "codigo_ibge", "taxa_entrega"]
        read_only_fields = ["id"]

    def validate_codigo_ibge(self, value):
        try:
            existe = codigo_municipio_existe(value)
        except IBGEUnavailable as exc:
            raise IBGEUnavailableAPIException(str(exc)) from exc
        except IBGEInvalidResponse as exc:
            raise IBGEInvalidResponseAPIException(str(exc)) from exc

        if not existe:
            raise serializers.ValidationError(
                "Este código IBGE não corresponde a um município válido."
            )
        return value


class NomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nome
        fields = ["id", "nome"]
        read_only_fields = ["id"]


class PedidoItemSerializer(serializers.ModelSerializer):
    produto_id = serializers.PrimaryKeyRelatedField(
        source="produto",
        queryset=Produto.objects.filter(disponivel=True),
        write_only=True,
    )
    produto = serializers.IntegerField(source="produto_id", read_only=True)
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = PedidoItem
        fields = [
            "produto",
            "produto_id",
            "produto_nome",
            "quantidade",
            "preco_unitario",
            "subtotal",
        ]
        read_only_fields = ["preco_unitario", "subtotal"]


class PedidoSerializer(serializers.ModelSerializer):
    itens = PedidoItemSerializer(many=True)
    area_entrega_id = serializers.PrimaryKeyRelatedField(
        source="area_entrega",
        queryset=AreaEntrega.objects.all(),
        write_only=True,
    )
    municipio = serializers.CharField(
        source="area_entrega.municipio",
        read_only=True,
    )
    usuario = serializers.PrimaryKeyRelatedField(read_only=True)
    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Pedido
        fields = [
            "id",
            "usuario",
            "cliente_nome",
            "telefone",
            "endereco",
            "area_entrega_id",
            "municipio",
            "taxa_entrega",
            "itens",
            "total",
            "status",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "usuario",
            "taxa_entrega",
            "total",
            "criado_em",
            "atualizado_em",
        ]

    def validate_status(self, value):
        request = self.context.get("request")
        if self.instance is None and value != Pedido.Status.PENDENTE:
            raise serializers.ValidationError(
                "Um pedido novo sempre começa como pendente."
            )
        if (
            self.instance is not None
            and request is not None
            and not request.user.is_staff
            and value != self.instance.status
        ):
            raise serializers.ValidationError(
                "Somente a equipe pode alterar o status do pedido."
            )
        return value

    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError(
                "O pedido precisa ter pelo menos um produto."
            )
        produtos = [item["produto"].pk for item in value]
        if len(produtos) != len(set(produtos)):
            raise serializers.ValidationError(
                "Cada produto deve aparecer uma única vez; ajuste a quantidade."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        itens_data = validated_data.pop("itens")
        area_entrega = validated_data["area_entrega"]
        pedido = Pedido.objects.create(
            **validated_data,
            usuario=self.context["request"].user,
            taxa_entrega=area_entrega.taxa_entrega,
        )
        for item_data in itens_data:
            produto = item_data["produto"]
            PedidoItem.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=item_data["quantidade"],
                preco_unitario=produto.preco,
            )
        return pedido

    @transaction.atomic
    def update(self, instance, validated_data):
        itens_data = validated_data.pop("itens", None)
        area_entrega = validated_data.get("area_entrega", instance.area_entrega)
        if "area_entrega" in validated_data:
            instance.area_entrega = area_entrega
            instance.taxa_entrega = area_entrega.taxa_entrega

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if itens_data is not None:
            instance.itens.all().delete()
            for item_data in itens_data:
                produto = item_data["produto"]
                PedidoItem.objects.create(
                    pedido=instance,
                    produto=produto,
                    quantidade=item_data["quantidade"],
                    preco_unitario=produto.preco,
                )
        return instance
