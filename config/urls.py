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
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from catalogo.views import (
    AreaEntregaViewSet,
    CategoriaViewSet,
    ProdutoViewSet,
    home,
    municipios_por_estado,
)

router = DefaultRouter()
router.register("categorias", CategoriaViewSet, basename="categoria")
router.register("produtos", ProdutoViewSet, basename="produto")
router.register("areas-entrega", AreaEntregaViewSet, basename="area-entrega")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("home/", home),
    path("api/token/", obtain_auth_token, name="api_token_auth"),
    path("api/municipios/", municipios_por_estado, name="municipios_por_estado"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api_schema"),
        name="api_docs",
    ),
    path("api/", include(router.urls)),
]
