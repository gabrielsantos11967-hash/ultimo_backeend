from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib import admin
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from .models import (
    AreaEntrega,
    Categoria,
    Nome,
    Pedido,
    Produto,
)
from .serializers import AreaEntregaSerializer


class CardapioApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.categoria = Categoria.objects.create(nome="Lanches")
        self.produto = Produto.objects.create(
            categoria=self.categoria,
            nome="X-Burguer",
            preco="18.50",
        )

    def test_pagina_inicial_exibe_dados_salvos_do_cardapio(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lanchonete do Bairro")
        self.assertContains(response, "Lanches")
        self.assertContains(response, "X-Burguer")
        self.assertContains(response, "18,50")
        self.assertContains(response, area.municipio)
        self.assertContains(response, str(area.codigo_ibge))

    def test_pagina_inicial_oculta_produtos_indisponiveis(self):
        self.produto.disponivel = False
        self.produto.save()

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "X-Burguer")
        self.assertContains(response, "Nenhum produto disponível cadastrado.")

    def test_cliente_pode_criar_conta_pelo_site(self):
        response = self.client.post(
            reverse("cadastro_cliente"),
            {
                "username": "cliente-novo",
                "password1": "SenhaForte123!abc",
                "password2": "SenhaForte123!abc",
            },
        )

        self.assertRedirects(response, reverse("home"))
        usuario = get_user_model().objects.get(username="cliente-novo")
        self.assertFalse(usuario.is_staff)
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_cliente_autenticado_pode_fazer_pedido_pelo_site(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        usuario = get_user_model().objects.create_user(
            username="cliente-site",
            password="SenhaForte123!abc",
        )
        self.client.force_login(usuario)

        response = self.client.post(
            reverse("home"),
            {
                "cliente_nome": "Cliente do site",
                "telefone": "81999999999",
                "endereco": "Rua Um, 10",
                "area_entrega_id": area.pk,
                "produto_id": [self.produto.pk],
                f"quantidade_{self.produto.pk}": "2",
            },
        )

        self.assertRedirects(response, reverse("home"))
        pedido = Pedido.objects.get(usuario=usuario)
        self.assertEqual(pedido.total, 44.50)
        self.assertEqual(pedido.itens.get().quantidade, 2)

    def test_cliente_precisa_escolher_produto_para_enviar_pedido_pelo_site(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        usuario = get_user_model().objects.create_user(
            username="cliente-sem-produto",
            password="SenhaForte123!abc",
        )
        self.client.force_login(usuario)

        response = self.client.post(
            reverse("home"),
            {
                "cliente_nome": "Cliente",
                "telefone": "81999999999",
                "endereco": "Rua Um, 10",
                "area_entrega_id": area.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O pedido precisa ter pelo menos um produto.")
        self.assertFalse(Pedido.objects.filter(usuario=usuario).exists())

    def test_lista_categorias_ativas_em_json(self):
        response = self.client.get(reverse("categoria-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [
            {
                "id": self.categoria.id,
                "nome": "Lanches",
                "descricao": "",
                "ativa": True,
            }
        ])

    def test_lista_produtos_disponiveis_com_categoria(self):
        response = self.client.get(reverse("produto-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [
            {
                "id": self.produto.id,
                "nome": "X-Burguer",
                "preco": "18.50",
                "disponivel": True,
                "categoria_nome": "Lanches",
            }
        ])

    def test_filtra_produtos_por_categoria(self):
        response = self.client.get(
            reverse("produto-list"),
            {"categoria": self.categoria.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_rejeita_categoria_invalida(self):
        response = self.client.get(
            reverse("produto-list"),
            {"categoria": "lanches"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("categoria", response.json())

    def test_oculta_produtos_indisponiveis_e_de_categorias_inativas(self):
        self.produto.disponivel = False
        self.produto.save()
        Produto.objects.create(
            categoria=self.categoria,
            nome="X-Salada",
            preco="20.00",
        )
        self.categoria.ativa = False
        self.categoria.save()

        response = self.client.get(reverse("produto-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_api_exige_autenticacao_para_criar_categoria(self):
        response = self.client.post(
            reverse("categoria-list"),
            {"nome": "Bebidas", "descricao": "", "ativa": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_token_autentica_usuario_para_criar_produto(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="gabriel",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        response = self.client.post(
            reverse("produto-list"),
            {
                "nome": "Refrigerante",
                "preco": "6.50",
                "disponivel": True,
                "categoria_id": self.categoria.id,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["categoria_nome"], "Lanches")

    def test_usuario_da_equipe_pode_atualizar_e_excluir_categoria(self):
        self.produto.delete()
        user = get_user_model().objects.create_user(
            username="editor",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        detalhe = reverse("categoria-detail", kwargs={"pk": self.categoria.pk})

        response = self.client.put(
            detalhe,
            {"nome": "Bebidas", "descricao": "Bebidas geladas", "ativa": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nome"], "Bebidas")

        response = self.client.delete(detalhe)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Categoria.objects.filter(pk=self.categoria.pk).exists())

    def test_usuario_da_equipe_pode_atualizar_e_excluir_produto(self):
        user = get_user_model().objects.create_user(
            username="editor-produto",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        detalhe = reverse("produto-detail", kwargs={"pk": self.produto.pk})
        dados = {
            "nome": "X-Burguer Especial",
            "preco": "22.00",
            "disponivel": True,
            "categoria_id": self.categoria.id,
        }

        response = self.client.put(detalhe, dados, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nome"], "X-Burguer Especial")

        response = self.client.delete(detalhe)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Produto.objects.filter(pk=self.produto.pk).exists())

    def test_api_aceita_preco_zero(self):
        user = get_user_model().objects.create_user(
            username="cliente-zero",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        response = self.client.post(
            reverse("produto-list"),
            {
                "nome": "Água cortesia",
                "preco": "0.00",
                "disponivel": True,
                "categoria_id": self.categoria.id,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["preco"], "0.00")

    def test_api_rejeita_preco_negativo(self):
        user = get_user_model().objects.create_user(
            username="cliente-negativo",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        response = self.client.post(
            reverse("produto-list"),
            {
                "nome": "Preço inválido",
                "preco": "-1.00",
                "disponivel": True,
                "categoria_id": self.categoria.id,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("preco", response.json())

    def test_filtra_produtos_por_disponibilidade(self):
        indisponivel = Produto.objects.create(
            categoria=self.categoria,
            nome="Milkshake",
            preco="12.00",
            disponivel=False,
        )
        user = get_user_model().objects.create_user(
            username="catalogo",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(
            reverse("produto-list"),
            {"disponivel": "false"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [produto["id"] for produto in response.json()["results"]],
            [indisponivel.id],
        )

    def test_busca_produtos_por_nome(self):
        Produto.objects.create(
            categoria=self.categoria,
            nome="Milkshake",
            preco="12.00",
        )

        response = self.client.get(
            reverse("produto-list"),
            {"search": "milk"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [produto["nome"] for produto in response.json()["results"]],
            ["Milkshake"],
        )

    def test_listagem_de_produtos_e_paginada(self):
        Produto.objects.bulk_create([
            Produto(
                categoria=self.categoria,
                nome=f"Lanche {indice}",
                preco="10.00",
            )
            for indice in range(11)
        ])

        response = self.client.get(reverse("produto-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 12)
        self.assertEqual(len(response.json()["results"]), 10)
        self.assertIsNotNone(response.json()["next"])

    def test_lista_produtos_da_categoria(self):
        response = self.client.get(
            reverse("categoria-produtos", kwargs={"pk": self.categoria.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [produto["nome"] for produto in response.json()["results"]],
            ["X-Burguer"],
        )

    def test_interface_navegavel_do_drf_disponivel(self):
        response = self.client.get(reverse("api-root"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("categorias", response.json())
        self.assertIn("produtos", response.json())

    @patch("catalogo.views.buscar_municipios")
    def test_lista_municipios_do_estado(self, buscar_municipios_mock):
        buscar_municipios_mock.return_value = [
            {"codigo_ibge": 2600054, "nome": "Abreu e Lima"},
            {"codigo_ibge": 2600104, "nome": "Afogados da Ingazeira"},
        ]

        response = self.client.get(
            reverse("municipios_por_estado"),
            {"uf": "pe"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "uf": "PE",
            "total": 2,
            "municipios": [
                {"codigo_ibge": 2600054, "nome": "Abreu e Lima"},
                {"codigo_ibge": 2600104, "nome": "Afogados da Ingazeira"},
            ],
        })
        buscar_municipios_mock.assert_called_once_with("PE")

    @patch("catalogo.views.buscar_municipios")
    def test_rejeita_sigla_de_estado_invalida(self, buscar_municipios_mock):
        response = self.client.get(
            reverse("municipios_por_estado"),
            {"uf": "XX"},
        )

        self.assertEqual(response.status_code, 400)
        buscar_municipios_mock.assert_not_called()

    def test_rejeita_uf_ausente(self):
        response = self.client.get(reverse("municipios_por_estado"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("erro", response.json())

    @patch("catalogo.views.buscar_municipios")
    def test_informa_indisponibilidade_do_ibge(self, buscar_municipios_mock):
        from .ibge import IBGEUnavailable

        buscar_municipios_mock.side_effect = IBGEUnavailable(
            "Não foi possível conectar à API do IBGE."
        )
        response = self.client.get(
            reverse("municipios_por_estado"),
            {"uf": "SP"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("erro", response.json())

    @patch("catalogo.ibge.requests.get")
    def test_consulta_ibge_com_timeout_e_formato_simplificado(
        self,
        requests_get_mock,
    ):
        from .ibge import buscar_municipios

        cache.delete("ibge_municipios_PE")
        response = requests_get_mock.return_value
        response.json.return_value = [
            {"id": 2600054, "nome": "Abreu e Lima", "microrregiao": {}},
        ]

        municipios = buscar_municipios("PE")

        self.assertEqual(
            municipios,
            [{"codigo_ibge": 2600054, "nome": "Abreu e Lima"}],
        )
        self.assertEqual(requests_get_mock.call_args.kwargs["timeout"], 10)

    @patch("catalogo.serializers.codigo_municipio_existe")
    def test_area_entrega_valida_codigo_ibge(self, codigo_existe_mock):
        codigo_existe_mock.return_value = True
        serializer = AreaEntregaSerializer(data={
            "municipio": "Abreu e Lima",
            "codigo_ibge": 2600054,
            "taxa_entrega": "7.50",
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        codigo_existe_mock.assert_called_once_with(2600054)

    @patch("catalogo.serializers.codigo_municipio_existe")
    def test_area_entrega_rejeita_codigo_ibge_inexistente(
        self,
        codigo_existe_mock,
    ):
        codigo_existe_mock.return_value = False
        serializer = AreaEntregaSerializer(data={
            "municipio": "Cidade inexistente",
            "codigo_ibge": 9999999,
            "taxa_entrega": "7.50",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("codigo_ibge", serializer.errors)

    @patch("catalogo.serializers.codigo_municipio_existe")
    def test_area_entrega_indica_indisponibilidade_do_ibge(
        self,
        codigo_existe_mock,
    ):
        from .ibge import IBGEUnavailable

        codigo_existe_mock.side_effect = IBGEUnavailable("IBGE indisponível.")
        serializer = AreaEntregaSerializer(data={
            "municipio": "Abreu e Lima",
            "codigo_ibge": 2600054,
            "taxa_entrega": "7.50",
        })

        with self.assertRaises(APIException) as context:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(context.exception.status_code, 503)

    def test_usuario_pode_obter_token(self):
        get_user_model().objects.create_user(
            username="token-user",
            password="senha-segura-123",
        )

        response = self.client.post(
            reverse("api_token_auth"),
            {"username": "token-user", "password": "senha-segura-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())

    @override_settings(DEBUG=True)
    def test_comando_exclui_cliente_e_mantem_gabriel_como_administrador(self):
        get_user_model().objects.create_user(
            username="cliente",
            password="cliente",
        )
        cliente_antigo = get_user_model().objects.get(username="cliente")
        cliente_antigo.is_staff = True
        cliente_antigo.is_superuser = True
        cliente_antigo.save(update_fields=["is_staff", "is_superuser"])
        cliente_antigo.groups.create(name="cliente_admin")

        with patch.dict(
            "os.environ",
            {
                "GABRIEL_ADMIN_PASSWORD": "123",
            },
        ):
            call_command("configurar_usuarios", stdout=StringIO())
        gabriel = get_user_model().objects.get(username="gabriel")
        self.assertTrue(gabriel.is_superuser)
        self.assertFalse(
            get_user_model().objects.filter(username="cliente").exists()
        )

        response = self.client.post(
            reverse("api_token_auth"),
            {"username": "gabriel", "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {response.json()['token']}"
        )
        response = self.client.get(reverse("produto-list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("api_token_auth"),
            {"username": "cliente", "password": "cliente"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("token", response.json())

    def test_lista_nomes_pelo_endpoint_nome(self):
        nome = Nome.objects.create(nome="Ana")

        response = self.client.get(reverse("nome-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [
            {"id": nome.id, "nome": "Ana"}
        ])

    def test_cria_detalha_atualiza_e_exclui_nome(self):
        usuario = get_user_model().objects.create_user(
            username="nome-editor",
            password="test-password",
        )
        usuario.is_staff = True
        usuario.save(update_fields=["is_staff"])
        self.client.force_authenticate(user=usuario)

        response = self.client.post(
            reverse("nome-list"),
            {"nome": "Bruno"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        nome_id = response.json()["id"]
        detalhe = reverse("nome-detail", kwargs={"pk": nome_id})

        response = self.client.get(detalhe)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": nome_id, "nome": "Bruno"})

        response = self.client.put(
            detalhe,
            {"nome": "Bruno Silva"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nome"], "Bruno Silva")

        response = self.client.patch(
            detalhe,
            {"nome": "Bruno Souza"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nome"], "Bruno Souza")

        response = self.client.delete(detalhe)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Nome.objects.filter(pk=nome_id).exists())

    def test_criar_nome_exige_autenticacao(self):
        response = self.client.post(
            reverse("nome-list"),
            {"nome": "Carla"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_cliente_le_catalogo_mas_nao_altera_dados_compartilhados(self):
        cliente = get_user_model().objects.create_user(
            username="cliente-api",
            password="senha-segura-123",
        )
        self.client.force_authenticate(user=cliente)

        response = self.client.get(reverse("produto-list"))
        self.assertEqual(response.status_code, 200)

        requests = (
            ("categoria-list", {"nome": "Bebidas"}),
            ("produto-list", {
                "nome": "Refrigerante",
                "preco": "6.50",
                "categoria_id": self.categoria.pk,
            }),
            ("nome-list", {"nome": "Ana"}),
            ("area-entrega-list", {
                "municipio": "Recife",
                "codigo_ibge": 2611606,
                "taxa_entrega": "7.50",
            }),
        )
        for route_name, data in requests:
            with self.subTest(route_name=route_name):
                response = self.client.post(
                    reverse(route_name),
                    data,
                    format="json",
                )
                self.assertEqual(response.status_code, 403)

    def test_usuario_autenticado_cria_e_consulta_proprio_pedido(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        usuario = get_user_model().objects.create_user(
            username="cliente-pedido",
            password="test-password",
        )
        self.client.force_authenticate(user=usuario)

        response = self.client.post(
            reverse("pedido-list"),
            {
                "cliente_nome": "Cliente de teste",
                "telefone": "81999999999",
                "endereco": "Rua Um, 10",
                "area_entrega_id": area.pk,
                "itens": [
                    {"produto_id": self.produto.pk, "quantidade": 2},
                ],
                "taxa_entrega": "0.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        pedido_id = response.data["id"]
        self.assertEqual(response.data["total"], "44.50")
        self.assertEqual(response.data["taxa_entrega"], "7.50")
        self.assertEqual(response.data["itens"][0]["preco_unitario"], "18.50")
        self.assertEqual(response.data["status"], Pedido.Status.PENDENTE)

        response = self.client.get(reverse("pedido-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        outro_usuario = get_user_model().objects.create_user(
            username="outro-cliente",
            password="test-password",
        )
        self.client.force_authenticate(user=outro_usuario)
        response = self.client.get(reverse("pedido-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertFalse(
            Pedido.objects.filter(
                pk=pedido_id,
                usuario=outro_usuario,
            ).exists()
        )

    def test_pedido_exige_autenticacao(self):
        response = self.client.get(reverse("pedido-list"))
        self.assertEqual(response.status_code, 401)

    def test_pedido_rejeita_lista_de_itens_vazia(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        usuario = get_user_model().objects.create_user(
            username="cliente-sem-itens",
            password="test-password",
        )
        self.client.force_authenticate(user=usuario)

        response = self.client.post(
            reverse("pedido-list"),
            {
                "cliente_nome": "Cliente",
                "telefone": "81999999999",
                "endereco": "Rua Um, 10",
                "area_entrega_id": area.pk,
                "itens": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("itens", response.data)

    def test_cliente_pode_alterar_apenas_pedido_proprio(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        dono = get_user_model().objects.create_user(
            username="dono-pedido",
            password="test-password",
        )
        pedido = Pedido.objects.create(
            usuario=dono,
            cliente_nome="Cliente",
            telefone="81999999999",
            endereco="Rua Um, 10",
            area_entrega=area,
            taxa_entrega=area.taxa_entrega,
        )
        usuario = get_user_model().objects.create_user(
            username="cliente-alteracao",
            password="test-password",
        )
        self.client.force_authenticate(user=dono)

        response = self.client.patch(
            reverse("pedido-detail", kwargs={"pk": pedido.pk}),
            {"telefone": "81988887777"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["telefone"], "81988887777")

        response = self.client.patch(
            reverse("pedido-detail", kwargs={"pk": pedido.pk}),
            {"status": Pedido.Status.CONCLUIDO},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        self.client.force_authenticate(user=usuario)
        response = self.client.get(
            reverse("pedido-detail", kwargs={"pk": pedido.pk})
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.patch(
            reverse("pedido-detail", kwargs={"pk": pedido.pk}),
            {"telefone": "81900000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_pode_alterar_status_do_pedido(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        usuario = get_user_model().objects.create_user(
            username="cliente-status",
            password="test-password",
        )
        pedido = Pedido.objects.create(
            usuario=usuario,
            cliente_nome="Cliente",
            telefone="81999999999",
            endereco="Rua Um, 10",
            area_entrega=area,
            taxa_entrega=area.taxa_entrega,
        )
        admin_user = get_user_model().objects.create_superuser(
            username="staff-pedidos",
            email="staff-pedidos@example.com",
            password="test-password",
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.patch(
            reverse("pedido-detail", kwargs={"pk": pedido.pk}),
            {"status": Pedido.Status.EM_PREPARO},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Pedido.Status.EM_PREPARO)

    def test_cliente_api_so_acessa_pedidos_proprios_e_nao_forja_proprietario(self):
        area = AreaEntrega.objects.create(
            municipio="Abreu e Lima",
            codigo_ibge=2600054,
            taxa_entrega="7.50",
        )
        cliente = get_user_model().objects.create_user(
            username="cliente-isolado",
            password="senha-segura-123",
        )
        outro_cliente = get_user_model().objects.create_user(
            username="outro-cliente-isolado",
            password="senha-segura-123",
        )
        pedido_alheio = Pedido.objects.create(
            usuario=outro_cliente,
            cliente_nome="Pedido privado",
            telefone="81999999999",
            endereco="Rua Um, 10",
            area_entrega=area,
            taxa_entrega=area.taxa_entrega,
        )
        self.client.force_authenticate(user=cliente)

        response = self.client.post(
            reverse("pedido-list"),
            {
                "usuario": outro_cliente.pk,
                "cliente_nome": "Pedido do cliente",
                "telefone": "81988887777",
                "endereco": "Rua Dois, 20",
                "area_entrega_id": area.pk,
                "itens": [
                    {"produto_id": self.produto.pk, "quantidade": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        pedido_proprio = Pedido.objects.get(pk=response.data["id"])
        self.assertEqual(pedido_proprio.usuario, cliente)
        self.assertEqual(response.data["usuario"], cliente.pk)

        response = self.client.get(reverse("pedido-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        detalhe_alheio = reverse(
            "pedido-detail",
            kwargs={"pk": pedido_alheio.pk},
        )
        for method, data in (
            (self.client.get, None),
            (self.client.patch, {"telefone": "81900000000"}),
            (self.client.delete, None),
        ):
            with self.subTest(method=method.__name__):
                response = (
                    method(detalhe_alheio, data, format="json")
                    if data is not None
                    else method(detalhe_alheio)
                )
                self.assertEqual(response.status_code, 404)

        pedido_alheio.refresh_from_db()
        self.assertEqual(pedido_alheio.telefone, "81999999999")


class CardapioAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        admin = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin)
        self.categoria = Categoria.objects.create(nome="Lanches")
        self.produto = Produto.objects.create(
            categoria=self.categoria,
            nome="X-Burguer",
            preco="18.50",
        )

    def test_painel_exibe_titulos_personalizados(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administração da Lanchonete")
        self.assertContains(response, "Gerenciamento do cardápio")

    @override_settings(DEBUG=True)
    def test_apenas_gabriel_gerencia_admin(self):
        get_user_model().objects.create_user(
            username="cliente",
            password="cliente",
        )
        with patch.dict(
            "os.environ",
            {
                "GABRIEL_ADMIN_PASSWORD": "123",
            },
        ):
            call_command("configurar_usuarios", stdout=StringIO())

        self.assertFalse(
            get_user_model().objects.filter(username="cliente").exists()
        )
        get_user_model().objects.create_user(
            username="cliente",
            password="cliente",
        )
        self.client.logout()
        self.assertTrue(self.client.login(username="cliente", password="cliente"))
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)

        self.client.logout()
        self.assertTrue(self.client.login(username="gabriel", password="123"))
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administração da Lanchonete")

    def test_listagem_de_categorias_exibe_contagem_de_produtos(self):
        response = self.client.get(
            reverse("admin:catalogo_categoria_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lanches")
        self.assertContains(response, "Produtos")
        self.assertContains(response, ">1<")

    def test_listagem_de_produtos_carrega(self):
        response = self.client.get(
            reverse("admin:catalogo_produto_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "X-Burguer")

    def test_admin_de_produto_tem_configuracao_solicitada(self):
        produto_admin = admin.site._registry[Produto]

        self.assertEqual(
            produto_admin.list_display,
            ("nome", "preco", "categoria", "disponivel"),
        )
        self.assertEqual(produto_admin.list_filter, ("categoria", "disponivel"))
        self.assertEqual(produto_admin.search_fields, ("nome",))
        self.assertEqual(produto_admin.list_editable, ("disponivel",))
        self.assertIn("marcar_indisponiveis", produto_admin.actions)
        self.assertEqual(
            produto_admin.marcar_indisponiveis.short_description,
            "Marcar como indisponível",
        )

    def test_area_entrega_esta_registrada_no_admin(self):
        area_admin = admin.site._registry[AreaEntrega]

        self.assertIn("municipio", area_admin.list_display)
        self.assertIn("codigo_ibge", area_admin.list_display)

    def test_produtos_sao_editaveis_dentro_da_categoria(self):
        categoria_admin = admin.site._registry[Categoria]

        self.assertTrue(
            any(inline.model is Produto for inline in categoria_admin.inlines)
        )

    def test_action_marca_produto_como_indisponivel(self):
        response = self.client.post(
            reverse("admin:catalogo_produto_changelist"),
            {
                "action": "marcar_indisponiveis",
                "_selected_action": [str(self.produto.pk)],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertFalse(self.produto.disponivel)
