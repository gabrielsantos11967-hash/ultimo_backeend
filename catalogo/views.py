from django.shortcuts import render
from rest_framework import status
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken

from .ibge import (
    IBGEInvalidResponse,
    IBGEUnavailable,
    IBGE_UFS,
    buscar_municipios,
)
from .models import AreaEntrega, Categoria, Nome, Pedido, Produto
from .serializers import (
    AreaEntregaSerializer,
    CategoriaSerializer,
    NomeSerializer,
    PedidoSerializer,
    ProdutoSerializer,
    ApiTokenSerializer,
)
from .permissions import ClienteSemAcessoApi


def home(request):
    categorias = Categoria.objects.filter(ativa=True)
    produtos = Produto.objects.filter(
        disponivel=True,
        categoria__ativa=True,
    ).select_related("categoria")
    areas_entrega = AreaEntrega.objects.all()

    return render(
        request,
        "catalogo/home.html",
        {
            "categorias": categorias,
            "produtos": produtos,
            "areas_entrega": areas_entrega,
        },
    )


class ApiTokenView(ObtainAuthToken):
    serializer_class = ApiTokenSerializer


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


class NomeViewSet(viewsets.ModelViewSet):
    queryset = Nome.objects.all()
    serializer_class = NomeSerializer


class PedidoViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Pedido.objects.select_related(
            "usuario",
            "area_entrega",
        ).prefetch_related("itens__produto")
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(usuario=self.request.user)

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            permission_classes = [ClienteSemAcessoApi, IsAdminUser]
        else:
            permission_classes = [ClienteSemAcessoApi, IsAuthenticated]
        return [permission() for permission in permission_classes]
