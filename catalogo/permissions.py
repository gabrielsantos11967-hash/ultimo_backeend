from rest_framework.permissions import BasePermission


CLIENTE_ADMIN_GROUP = "cliente_admin"


def is_cliente_admin(user):
    return (
        user.is_authenticated
        and user.groups.filter(name=CLIENTE_ADMIN_GROUP).exists()
    )


class ClienteSemAcessoApi(BasePermission):
    message = "A conta cliente não tem permissão para acessar a API."

    def has_permission(self, request, view):
        return not is_cliente_admin(request.user)
