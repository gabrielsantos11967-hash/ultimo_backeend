"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalogo.views import (
    AreaEntregaViewSet,
    ApiTokenView,
    CategoriaViewSet,
    NomeViewSet,
    PedidoViewSet,
    ProdutoViewSet,
    cadastro_cliente,
    home,
    meus_pedidos,
    municipios_por_estado,
)

router = DefaultRouter()
router.register("nome", NomeViewSet, basename="nome")
router.register("categorias", CategoriaViewSet, basename="categoria")
router.register("produtos", ProdutoViewSet, basename="produto")
router.register("areas-entrega", AreaEntregaViewSet, basename="area-entrega")
router.register("pedidos", PedidoViewSet, basename="pedido")

urlpatterns = [
    path("", home, name="home"),
    path("meus-pedidos/", meus_pedidos, name="meus_pedidos"),
    path("admin/", admin.site.urls),
    path("home/", home),
    path(
        "entrar/",
        auth_views.LoginView.as_view(
            template_name="catalogo/login.html",
            next_page="home",
        ),
        name="login",
    ),
    path(
        "sair/",
        auth_views.LogoutView.as_view(next_page="home"),
        name="logout",
    ),
    path("cadastro/", cadastro_cliente, name="cadastro_cliente"),
    path("api/token/", ApiTokenView.as_view(), name="api_token_auth"),
    path("api/municipios/", municipios_por_estado, name="municipios_por_estado"),
    path("api/", include(router.urls)),
]
