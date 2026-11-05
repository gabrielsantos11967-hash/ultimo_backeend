# ultimo_backeend

## Cardápio

`Categoria` possui nome único e descrição opcional. `Produto` possui nome de
até 150 caracteres, preço decimal não negativo, disponibilidade e uma categoria
relacionada por `ForeignKey` (`related_name="produtos"`). Ambos convertem para o
nome no método `__str__`.

O cadastro de categorias e produtos é feito no painel do Django:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/admin/` e cadastre categorias e produtos. O
painel está em português, permite adicionar produtos diretamente na edição de
uma categoria, editar a disponibilidade pela listagem e filtrar ou pesquisar
produtos por nome. A ação em lote permite marcar produtos como indisponíveis.
Crie o primeiro usuário administrativo com `python manage.py createsuperuser`;
em seguida, use o painel para cadastrar pelo menos 3 categorias e 10 produtos.

O fixture `catalogo/fixtures/cardapio.json` contém 3 categorias e 10 produtos
de exemplo. Para carregar os dados em um banco vazio, execute:

```bash
python manage.py loaddata cardapio
```

O fixture foi exportado com `dumpdata` e não inclui usuários ou senhas.

API REST:

- `/api/categorias/` e `/api/produtos/` oferecem CRUD completo.
- `/api/areas-entrega/` oferece CRUD das áreas atendidas; o código do município
  é validado no IBGE antes de salvar.
- `GET /api/produtos/?categoria=1` filtra pelo ID da categoria.
- `GET /api/produtos/?disponivel=true` filtra por disponibilidade.
- `GET /api/produtos/?search=burguer` busca no nome do produto.
- `GET /api/categorias/1/produtos/` lista os produtos de uma categoria.
- `GET /api/municipios/?uf=PE` consulta os municípios na API pública do IBGE e
  devolve UF, total e itens com `codigo_ibge` e `nome`.
- `POST /api/token/` recebe `username` e `password` e devolve um token.
- `/api/docs/` abre a documentação Swagger; `/api/schema/` fornece o schema.

As rotas CRUD são registradas com o `DefaultRouter` do Django REST Framework.
Leitura é pública; criação, edição e exclusão exigem autenticação por token ou
sessão. Envie o token no cabeçalho `Authorization: Token <token>`. Na escrita
de produtos, informe `categoria_id`; a resposta inclui `categoria_nome`.
As listagens são paginadas e o preço é enviado como texto decimal, por exemplo
`"18.50"`.

A lista de municípios é consultada no IBGE com timeout de 10 segundos,
armazenada em cache por 24 horas e não é persistida no banco. Use a sigla de
uma UF brasileira; em caso de indisponibilidade do IBGE, o endpoint responde
com HTTP 503.

Uma área de entrega registra `municipio`, `codigo_ibge` e `taxa_entrega`.
O serializer verifica o código no endpoint público de municípios do IBGE antes
de permitir o cadastro.