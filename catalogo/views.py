from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from rest_framework import status
from rest_framework import serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
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


def home(request):
    categorias = Categoria.objects.filter(ativa=True)
    produtos = Produto.objects.filter(
        disponivel=True,
        categoria__ativa=True,
    ).select_related("categoria")
    areas_entrega = AreaEntrega.objects.all()

    context = {
        "categorias": categorias,
        "produtos": produtos,
        "areas_entrega": areas_entrega,
        "order_errors": [],
        "form_data": request.POST,
        "selected_products": [
            int(product_id)
            for product_id in request.POST.getlist("produto_id")
            if product_id.isdecimal()
        ],
    }

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Entre na sua conta para enviar o pedido.")
            return redirect("login")

        pedido_data = {
            "cliente_nome": request.POST.get("cliente_nome", ""),
            "telefone": request.POST.get("telefone", ""),
            "endereco": request.POST.get("endereco", ""),
            "area_entrega_id": request.POST.get("area_entrega_id", ""),
            "itens": [
                {
                    "produto_id": produto_id,
                    "quantidade": request.POST.get(
                        f"quantidade_{produto_id}",
                        "",
                    ),
                }
                for produto_id in request.POST.getlist("produto_id")
            ],
        }
        serializer = PedidoSerializer(
            data=pedido_data,
            context={"request": request},
        )
        if serializer.is_valid():
            pedido = serializer.save()
            messages.success(
                request,
                f"Pedido #{pedido.pk} enviado! Total: R$ {pedido.total:.2f}.",
            )
            return redirect("home")

        context["order_errors"] = [
            f"{field}: {', '.join(str(error) for error in errors)}"
            for field, errors in serializer.errors.items()
        ]

    return render(request, "catalogo/home.html", context)


def cadastro_cliente(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(
            request,
            "Conta criada. Agora você já pode fazer seu pedido.",
        )
        return redirect("home")

    return render(request, "catalogo/cadastro.html", {"form": form})


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
