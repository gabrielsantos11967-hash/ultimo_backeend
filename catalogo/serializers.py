from rest_framework import serializers

from rest_framework.exceptions import APIException

from .ibge import (
    IBGEInvalidResponse,
    IBGEUnavailable,
    codigo_municipio_existe,
)
from .models import AreaEntrega, Categoria, Produto


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
