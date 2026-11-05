import os
import sys
from getpass import getpass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError

from catalogo.models import (
    AreaEntrega,
    Categoria,
    Nome,
    Pedido,
    PedidoItem,
    Produto,
)
from catalogo.permissions import CLIENTE_ADMIN_GROUP


class Command(BaseCommand):
    help = "Cria o administrador Gabriel e configura a conta cliente do Admin."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Este comando com credenciais locais só pode ser usado "
                "com DEBUG=True."
            )

        passwords = {}
        for username, variable in (
            ("gabriel", "GABRIEL_ADMIN_PASSWORD"),
            ("cliente", "CLIENTE_ADMIN_PASSWORD"),
        ):
            password = os.environ.get(variable)
            if password is None:
                if not sys.stdin.isatty():
                    raise CommandError(
                        f"Defina {variable} ou execute o comando em um terminal."
                    )
                password = getpass(f"Senha para {username}: ")
                confirmation = getpass(f"Confirme a senha de {username}: ")
                if not password or password != confirmation:
                    raise CommandError(
                        f"As senhas de {username} estão vazias ou não conferem."
                    )
            if not password:
                raise CommandError(f"A senha de {username} não pode ficar vazia.")
            passwords[username] = password

        user_model = get_user_model()
        gabriel = self._get_or_create_user(user_model, "gabriel")
        gabriel.is_active = True
        gabriel.is_staff = True
        gabriel.is_superuser = True
        gabriel.set_password(passwords["gabriel"])
        gabriel.save()

        cliente = self._get_or_create_user(user_model, "cliente")
        cliente.is_active = True
        cliente.is_staff = True
        cliente.is_superuser = False
        cliente.set_password(passwords["cliente"])
        cliente.user_permissions.clear()
        cliente.save()

        group, _ = Group.objects.get_or_create(name=CLIENTE_ADMIN_GROUP)
        group.permissions.set(self._cliente_admin_permissions())
        cliente.groups.set([group])

        self.stdout.write(
            self.style.SUCCESS(
                "Contas gabriel (administrador total) e cliente "
                "(gerenciamento do catálogo no Django Admin, sem acesso à API) "
                "configuradas."
            )
        )

    @staticmethod
    def _get_or_create_user(user_model, username):
        user, _ = user_model.objects.get_or_create(username=username)
        return user

    @staticmethod
    def _cliente_admin_permissions():
        editable_models = (
            AreaEntrega,
            Categoria,
            Nome,
            Pedido,
            PedidoItem,
            Produto,
        )
        view_only_models = (get_user_model(),)
        permissions = []
        for model in editable_models:
            permissions.extend(
                Command._permissions_for_model(
                    model,
                    ("add", "change", "delete", "view"),
                )
            )
        for model in view_only_models:
            permissions.extend(
                Command._permissions_for_model(model, ("view",))
            )
        return permissions

    @staticmethod
    def _permissions_for_model(model, actions):
        permissions = []
        content_type = ContentType.objects.get_for_model(model)
        for action in actions:
            codename = f"{action}_{model._meta.model_name}"
            try:
                permissions.append(
                    Permission.objects.get(
                        content_type=content_type,
                        codename=codename,
                    )
                )
            except Permission.DoesNotExist as exc:
                raise CommandError(
                    "Permissões ainda não foram criadas. Execute "
                    "`python manage.py migrate` antes deste comando."
                ) from exc
        return permissions
