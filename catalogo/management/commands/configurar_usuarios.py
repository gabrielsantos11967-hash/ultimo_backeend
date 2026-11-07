import os
import sys
from getpass import getpass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Cria o administrador Gabriel e remove a conta cliente antiga."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Este comando com credenciais locais só pode ser usado "
                "com DEBUG=True."
            )

        password = os.environ.get("GABRIEL_ADMIN_PASSWORD")
        if password is None:
            if not sys.stdin.isatty():
                raise CommandError(
                    "Defina GABRIEL_ADMIN_PASSWORD ou execute o comando "
                    "em um terminal."
                )
            password = getpass("Senha para gabriel: ")
            confirmation = getpass("Confirme a senha de gabriel: ")
            if not password or password != confirmation:
                raise CommandError(
                    "As senhas de gabriel estão vazias ou não conferem."
                )
        if not password:
            raise CommandError("A senha de gabriel não pode ficar vazia.")

        user_model = get_user_model()
        gabriel = self._get_or_create_user(user_model, "gabriel")
        gabriel.is_active = True
        gabriel.is_staff = True
        gabriel.is_superuser = True
        gabriel.set_password(password)
        gabriel.save()

        cliente_antigo = user_model.objects.filter(username="cliente").first()
        if cliente_antigo is not None:
            try:
                cliente_antigo.delete()
            except ProtectedError as exc:
                raise CommandError(
                    "A conta cliente não pode ser excluída porque há dados "
                    "vinculados protegidos no banco."
                ) from exc

        mensagem = "Conta gabriel (administrador total) configurada."
        if cliente_antigo is not None:
            mensagem += " A conta cliente antiga foi excluída."
        self.stdout.write(self.style.SUCCESS(mensagem))

    @staticmethod
    def _get_or_create_user(user_model, username):
        user, _ = user_model.objects.get_or_create(username=username)
        return user
