from django.http import HttpResponse
from rest_framework import status
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, extend_schema

from .ibge import (
    IBGEInvalidResponse,
    IBGEUnavailable,
    IBGE_UFS,
    buscar_municipios,
)
from .models import AreaEntrega, Categoria, Produto
from .serializers import (
    AreaEntregaSerializer,
    CategoriaSerializer,
    ProdutoSerializer,
)


def home(request):
    return HttpResponse("Bem-vindoo!")


class MunicipioSerializer(serializers.Serializer):
    codigo_ibge = serializers.IntegerField()
    nome = serializers.CharField()


class MunicipiosResponseSerializer(serializers.Serializer):
    uf = serializers.CharField()
    total = serializers.IntegerField()
    municipios = MunicipioSerializer(many=True)


class ErroMunicipiosSerializer(serializers.Serializer):
    erro = serializers.CharField()


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="uf",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Sigla da unidade federativa, por exemplo PE.",
        )
    ],
    responses={
        200: MunicipiosResponseSerializer,
        400: ErroMunicipiosSerializer,
        503: ErroMunicipiosSerializer,
    },
)
@api_view(["GET"])
def municipios_por_estado(request):
    uf = request.query_params.get("uf", "").strip().upper()
    if uf not in IBGE_UFS:
        return Response(
            {"erro": "Informe uma sigla válida de estado brasileiro."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        municipios = buscar_municipios(uf)
    except IBGEUnavailable as exc:
        return Response(
            {"erro": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except IBGEInvalidResponse as exc:
        return Response(
            {"erro": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({
        "uf": uf,
        "total": len(municipios),
        "municipios": municipios,
    })


class CategoriaViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer

    def get_queryset(self):
        queryset = Categoria.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(ativa=True)
        return queryset

    @action(detail=True, methods=["get"], url_path="produtos")
    def produtos(self, request, pk=None):
        categoria = self.get_object()
        queryset = Produto.objects.filter(categoria=categoria).select_related(
            "categoria"
        )
        if not request.user.is_authenticated:
            queryset = queryset.filter(disponivel=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProdutoSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProdutoSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)


class ProdutoViewSet(viewsets.ModelViewSet):
    serializer_class = ProdutoSerializer
    filter_backends = [SearchFilter]
    search_fields = ["nome"]

    def get_queryset(self):
        queryset = Produto.objects.select_related("categoria")
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(
                disponivel=True,
                categoria__ativa=True,
            )
        elif not self.request.user.is_staff:
            queryset = queryset.filter(categoria__ativa=True)

        disponibilidade = self.request.query_params.get("disponivel")
        if disponibilidade is not None:
            disponivel = serializers.BooleanField().to_internal_value(
                disponibilidade
            )
            queryset = queryset.filter(disponivel=disponivel)

        categoria_id = self.request.query_params.get("categoria")
        if categoria_id:
            if not categoria_id.isdecimal():
                raise serializers.ValidationError(
                    {"categoria": "Informe um ID de categoria válido."}
                )
            queryset = queryset.filter(categoria_id=int(categoria_id))
        return queryset


class AreaEntregaViewSet(viewsets.ModelViewSet):
    queryset = AreaEntrega.objects.all()
    serializer_class = AreaEntregaSerializer
