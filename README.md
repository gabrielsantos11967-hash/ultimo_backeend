# Lanchonete do Bairro — API de cardápio e entregas

**Autor:** Gabriel Santos Ferreira de Andrade

Este projeto é uma aplicação Django para organizar o cardápio de uma
lanchonete. O painel administrativo permite cadastrar categorias, produtos,
áreas de entrega e registros de nomes. A API REST disponibiliza operações de
consulta e manutenção desses dados, autenticação por token e consulta dos
municípios brasileiros na API pública do IBGE.

## Tecnologias utilizadas

| Tecnologia | Para que serve |
|---|---|
| Python | Linguagem usada para implementar o projeto. |
| Django | Framework que fornece a estrutura web, ORM, migrações e painel administrativo. |
| Django REST Framework (DRF) | Cria endpoints REST, serializers, viewsets, autenticação e interface navegável da API. |
| SQLite | Banco de dados usado por padrão neste projeto. |
| Requests | Faz requisições HTTP à API pública do IBGE. |
| API de localidades do IBGE | Fornece municípios e códigos oficiais sem exigir chave de acesso. |

## Requisitos

- Python instalado.
- Git para clonar o repositório.
- Acesso à internet para instalar dependências e consultar o IBGE.

## Como instalar e executar no Windows

No terminal, clone o repositório e entre na pasta. Substitua o endereço abaixo
pela URL do repositório:

```powershell
git clone <URL_DO_REPOSITORIO>
cd ultimo_backeend
```

Crie e ative o ambiente virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação do ambiente, abra o Prompt de Comando e
use `venv\Scripts\activate.bat`.

Instale as dependências e prepare o banco:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
```

Configure a conta administrativa local. O comando solicitará a senha sem
mostrá-la na tela:

```powershell
python manage.py configurar_usuarios
```

Use `gabriel` para acesso total ao Admin e à API. Clientes devem ter contas
comuns criadas pelo administrador; eles entram na API com token e só podem
consultar ou alterar os próprios pedidos. O catálogo pode ser consultado por
todos, mas só usuários da equipe podem alterá-lo. Se existir, a conta chamada
`cliente` será excluída; crie contas individuais para clientes que usarão a API.
O comando exige `DEBUG=True`, não deve ser executado em produção e redefine a
senha de `gabriel` sempre que for executado. Se a conta `cliente` tiver dados
vinculados protegidos, o comando interrompe a exclusão para preservar esses
registros.

Opcionalmente, carregue os dados demonstrativos do cardápio:

```powershell
python manage.py loaddata cardapio
```

O fixture fica em `catalogo/fixtures/cardapio.json` e contém registros de
categorias e produtos. Carregue-o em um banco ainda sem esses mesmos registros,
pois nomes duplicados ou IDs já utilizados podem causar conflito.

Inicie o servidor local:

```powershell
python manage.py runserver
```

O servidor de desenvolvimento ficará em `http://127.0.0.1:8000/`. Para parar,
pressione `Ctrl+C` no terminal.

## Acessos

- Interface navegável da API (DRF): http://127.0.0.1:8000/api/
- Página inicial com tabelas do cardápio: http://127.0.0.1:8000/
- Painel administrativo: http://127.0.0.1:8000/admin/
- Consulta de municípios (exemplo): http://127.0.0.1:8000/api/municipios/?uf=PE

O endereço `127.0.0.1` é local: só pode ser acessado enquanto o servidor estiver
rodando no próprio computador. As contas são criadas pelo comando
`configurar_usuarios`; as senhas não ficam salvas no código ou no fixture.

## Para que servem os comandos

| Comando | Para que serve |
|---|---|
| `python -m venv venv` | Cria um ambiente virtual chamado `venv`, isolando as dependências deste projeto. |
| `.\venv\Scripts\Activate.ps1` | Ativa o ambiente virtual no PowerShell do Windows. No Prompt de Comando, use `venv\Scripts\activate.bat`. |
| `source venv/bin/activate` | Ativa o ambiente virtual no Linux ou macOS; é uma alternativa aos comandos de ativação do Windows. |
| `python -m pip install -r requirements.txt` | Instala as dependências e versões listadas no arquivo `requirements.txt`. |
| `pip install django djangorestframework` | Instala Django e Django REST Framework manualmente. Neste projeto, prefira instalar pelo `requirements.txt`. |
| `pip install requests` | Instala a biblioteca de requisições HTTP, usada neste projeto para consultar o IBGE. Ela já está listada em `requirements.txt`. |
| `pip freeze > requirements.txt` | Salva no arquivo as versões das bibliotecas instaladas no ambiente ativo. Use com cuidado: também pode incluir pacotes que não são dependências diretas do projeto. |
| `python manage.py makemigrations` | Cria arquivos de migração a partir de mudanças nos modelos. |
| `python manage.py migrate` | Aplica as migrações e cria ou atualiza as tabelas no banco de dados. |
| `python manage.py createsuperuser` | Cria manualmente uma conta de superusuário do Django. Neste projeto, use `python manage.py configurar_usuarios` para configurar o administrador `gabriel`. |
| `python manage.py runserver` | Inicia o servidor de desenvolvimento, normalmente em `http://127.0.0.1:8000/`. |
| `python manage.py dumpdata catalogo --indent 2 > catalogo.json` | Exporta os registros do app `catalogo` para um arquivo JSON formatado. |
| `python manage.py loaddata catalogo.json` | Importa dados de um arquivo JSON para o banco. Se os registros já existirem, IDs ou restrições podem causar conflitos. |

Os comandos abaixo são usados para **criar um projeto novo** e não devem ser
executados neste repositório, que já possui o projeto `config` e o app
`catalogo`:

```text
django-admin startproject lanchonete .
python manage.py startapp cardapio
```

O primeiro cria a estrutura de um projeto Django; o ponto final indica a pasta
atual. O segundo cria um app Django. Aqui, o app existente é `catalogo`, não
`cardapio`. Para ativar o ambiente virtual no Linux ou macOS, use o comando
`source venv/bin/activate`, em vez do comando de ativação do Windows.

## Como o projeto está organizado

| Arquivo | Papel |
|---|---|
| `config/settings.py` | Configura o projeto, apps instalados, banco SQLite, idioma, fuso horário, autenticação, permissões e paginação do DRF. |
| `config/urls.py` | Define as URLs do Admin, da API, da autenticação por token e da consulta de municípios; registra os viewsets no router. |
| `catalogo/models.py` | Define as tabelas e regras de dados: `Categoria`, `Produto`, `AreaEntrega`, `Nome`, `Pedido` e `PedidoItem`. |
| `catalogo/serializers.py` | Converte models para JSON e valida dados recebidos pela API, inclusive preço e código IBGE. |
| `catalogo/views.py` | Implementa os viewsets CRUD, filtros, busca, lista de produtos por categoria e endpoint de municípios. |
| `catalogo/admin.py` | Registra e personaliza os models no Django Admin, com filtros, edição em linha e ação em lote de disponibilidade. |
| `catalogo/management/commands/configurar_usuarios.py` | Cria o administrador de acesso total e exclui a conta `cliente` antiga, se não houver dados protegidos vinculados. |
| `catalogo/templates/catalogo/home.html` | Exibe as tabelas públicas de categorias, produtos disponíveis e áreas de entrega na página inicial. |
| `catalogo/ibge.py` | Consulta o IBGE com `requests`, timeout e cache; simplifica a resposta e verifica códigos de município. |
| `catalogo/migrations/` | Guarda as migrações que criam e alteram a estrutura do banco. |
| `catalogo/fixtures/cardapio.json` | Contém dados de exemplo carregáveis com `loaddata`. |
| `requirements.txt` | Lista as bibliotecas Python necessárias para executar o projeto. |

## Conceitos da API

- **API REST:** forma de disponibilizar recursos por URLs e métodos HTTP,
  normalmente usando JSON.
- **Model:** representação, no Django, dos dados que serão armazenados no
  banco.
- **Serializer:** converte dados do model em JSON e valida o JSON recebido.
- **ViewSet:** reúne as operações de consulta e alteração de um recurso.
- **Router:** cria automaticamente as URLs de um viewset, como listagem e
  detalhes.
- **GET:** consulta/lista dados.
- **POST:** cria um registro.
- **PUT:** substitui/atualiza um registro.
- **PATCH:** atualiza parcialmente um registro.
- **DELETE:** remove um registro.

As listagens do cardápio são públicas; alterações de categorias, produtos,
nomes e áreas de entrega são restritas a usuários da equipe. Pedidos exigem
autenticação por sessão ou token: cada cliente só lista, consulta, altera ou
exclui pedidos associados à própria conta. O cliente não pode alterar o status;
essa ação fica com a equipe. A conta `gabriel` tem acesso total ao Admin e à
API. O token é enviado no cabeçalho
`Authorization: Token <token>`.

Para obter um token, envie `POST /api/token/` com as credenciais de uma conta
autorizada para a API:

```json
{
  "username": "seu_usuario",
  "password": "sua_senha"
}
```

Resposta:

```json
{
  "token": "token-gerado-pelo-django"
}
```

## Endpoints

| Endpoint | Métodos | O que faz |
|---|---|---|
| `/api/` | GET | Mostra a interface navegável do DRF e links para os recursos. |
| `/api/nome/` | GET, POST | Lista ou cria registros que contêm um nome. |
| `/api/nome/{id}/` | GET, PUT, PATCH, DELETE | Detalha, atualiza ou remove um registro de nome. |
| `/api/categorias/` | GET, POST | Lista ou cria categorias. |
| `/api/categorias/{id}/` | GET, PUT, PATCH, DELETE | Detalha, atualiza ou remove uma categoria. |
| `/api/categorias/{id}/produtos/` | GET | Lista os produtos de uma categoria. |
| `/api/produtos/` | GET, POST | Lista ou cria produtos. |
| `/api/produtos/{id}/` | GET, PUT, PATCH, DELETE | Detalha, atualiza ou remove um produto. |
| `/api/areas-entrega/` | GET, POST | Lista ou cadastra áreas de entrega. |
| `/api/areas-entrega/{id}/` | GET, PUT, PATCH, DELETE | Detalha, atualiza ou remove uma área de entrega. |
| `/api/pedidos/` | GET, POST | Lista os pedidos do usuário autenticado ou cria um pedido. |
| `/api/pedidos/{id}/` | GET, PUT, PATCH, DELETE | Consulta pedido próprio; funcionários podem alterar ou excluir pedidos. |
| `/api/municipios/?uf=PE` | GET | Consulta municípios de uma UF no IBGE e retorna o total. |
| `/api/token/` | POST | Valida usuário e senha e retorna um token de autenticação. |

Clientes comuns não acessam `/admin/`; esse painel requer uma conta da equipe.
As alterações do catálogo também são reservadas à equipe. No endpoint de
pedidos, cada cliente só recebe os pedidos ligados à própria conta: tentar
consultar, alterar ou excluir o pedido de outra pessoa retorna `404`. Ao criar
um pedido, a API define o proprietário pelo usuário autenticado e ignora
qualquer `usuario` enviado no corpo.

Parâmetros de consulta para produtos:

- `/api/produtos/?categoria=1` filtra pelo ID da categoria.
- `/api/produtos/?disponivel=true` filtra pela disponibilidade (`true` ou
  `false`).
- `/api/produtos/?search=burguer` procura o texto no nome do produto.
- `/api/produtos/?page=2` acessa outra página da listagem.

### Exemplos de envio e resposta

Criar uma categoria (`POST /api/categorias/`):

```json
{
  "nome": "Lanches",
  "descricao": "Hambúrgueres e sanduíches",
  "ativa": true
}
```

Resposta de exemplo:

```json
{
  "id": 1,
  "nome": "Lanches",
  "descricao": "Hambúrgueres e sanduíches",
  "ativa": true
}
```

Criar um produto (`POST /api/produtos/`). O campo `categoria_id` indica a
categoria; o nome dela aparece na resposta como `categoria_nome`:

```json
{
  "nome": "X-Burguer",
  "preco": "18.50",
  "disponivel": true,
  "categoria_id": 1
}
```

Resposta de exemplo:

```json
{
  "id": 1,
  "nome": "X-Burguer",
  "preco": "18.50",
  "disponivel": true,
  "categoria_nome": "Lanches"
}
```

Criar um registro no recurso de nomes (`POST /api/nome/`):

```json
{
  "nome": "Ana"
}
```

Resposta:

```json
{
  "id": 1,
  "nome": "Ana"
}
```

Criar uma área de entrega (`POST /api/areas-entrega/`):

```json
{
  "municipio": "Abreu e Lima",
  "codigo_ibge": 2600054,
  "taxa_entrega": "7.50"
}
```

O serializer confirma no IBGE se o código existe antes de salvar. Se não
existir, o campo `codigo_ibge` retorna erro de validação.

Criar um pedido (`POST /api/pedidos/`) requer autenticação e uma área de
entrega previamente cadastrada:

```json
{
  "cliente_nome": "Ana",
  "telefone": "81999999999",
  "endereco": "Rua Um, 10",
  "area_entrega_id": 1,
  "itens": [
    {
      "produto_id": 1,
      "quantidade": 2
    }
  ]
}
```

O preço dos produtos e a taxa de entrega são obtidos do banco no momento da
criação; o cliente não pode informar esses valores. A resposta inclui os itens,
subtotal de cada item, total e status inicial `pendente`. Cada cliente consulta
e altera apenas os próprios pedidos. A view filtra também as consultas por ID,
de modo que um pedido de outra conta não fica visível ao cliente. A equipe
autenticada como funcionário pode consultar todos, atualizar status e gerenciar
pedidos.

Exemplo resumido de resposta:

```json
{
  "id": 1,
  "cliente_nome": "Ana",
  "telefone": "81999999999",
  "endereco": "Rua Um, 10",
  "municipio": "Abreu e Lima",
  "taxa_entrega": "7.50",
  "itens": [
    {
      "produto": 1,
      "produto_nome": "X-Burguer",
      "quantidade": 2,
      "preco_unitario": "18.50",
      "subtotal": "37.00"
    }
  ],
  "total": "44.50",
  "status": "pendente"
}
```

### Consulta de municípios do IBGE

O endpoint público é:

```text
GET /api/municipios/?uf=PE
```

Ele usa esta URL do IBGE, substituindo `{UF}` pela sigla informada:

```text
https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios
```

Exemplo de resposta simplificada:

```json
{
  "uf": "PE",
  "total": 185,
  "municipios": [
    {
      "codigo_ibge": 2600054,
      "nome": "Abreu e Lima"
    },
    {
      "codigo_ibge": 2600104,
      "nome": "Afogados da Ingazeira"
    }
  ]
}
```

A quantidade e os dados são fornecidos pelo IBGE. A aplicação valida a sigla,
usa timeout de 10 segundos e guarda a resposta em cache por 24 horas. UF
ausente ou inválida retorna HTTP 400; falha ou demora do IBGE retorna HTTP 503.
Uma resposta inválida do serviço externo retorna HTTP 502. A consulta não
salva todos os municípios no banco.

### Código do endpoint

Em `catalogo/views.py`, o endpoint valida a UF, consulta a função de integração
com o IBGE e retorna os municípios em JSON:

```python
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
```

### Teste e resposta do endpoint

Com o servidor iniciado por `python manage.py runserver`, consulte:

```text
http://127.0.0.1:8000/api/municipios/?uf=PE
```

Resposta real verificada em 05/11/2026: **HTTP 200**, com 185 municípios para
Pernambuco. Abaixo estão os dois primeiros itens retornados:

```json
{
  "uf": "PE",
  "total": 185,
  "municipios": [
    {
      "codigo_ibge": 2600054,
      "nome": "Abreu e Lima"
    },
    {
      "codigo_ibge": 2600104,
      "nome": "Afogados da Ingazeira"
    }
  ]
}
```

## Django Admin

Entre em http://127.0.0.1:8000/admin/ com `gabriel` para gerenciar todos os
dados. Clientes usam os endpoints da API com suas contas comuns; eles não têm
acesso ao Django Admin, não alteram o catálogo e só podem operar sobre os
próprios pedidos. O cabeçalho do painel foi personalizado para
“Administração da Lanchonete”.

- Categorias e produtos podem ser gerenciados no Admin.
- Produtos podem ser editados dentro da tela da categoria usando
  `TabularInline`.
- A listagem de produtos mostra nome, preço, categoria e disponibilidade.
- É possível filtrar por categoria/disponibilidade e pesquisar pelo nome.
- A disponibilidade é editável diretamente na listagem.
- A ação “Marcar como indisponível” altera os produtos selecionados.
- As áreas de entrega e registros de nomes também estão registrados.
- Pedidos mostram cliente, município, status, total e data; seus itens podem
  ser consultados/gerenciados na tela de cada pedido. O funcionário pode alterar
  o status do pedido no Admin.

Um pedido guarda o cliente, telefone, endereço, usuário, área e taxa de entrega
registrada no momento. Cada `PedidoItem` guarda o produto, a quantidade e o
preço unitário daquele momento, para que mudanças futuras de preço não alterem
pedidos antigos.

### Capturas de tela

O repositório não contém capturas de tela. Caso sejam necessárias para a
apresentação do projeto, recomenda-se incluí-las nos seguintes caminhos:

1. `docs/imagens/api-drf.png`: interface navegável da API em `/api/`.
2. `docs/imagens/admin-cardapio.png`: listagem de produtos ou edição de
   categoria no Django Admin, acessível em `/admin/`.

As imagens não devem conter senhas, tokens ou outros dados privados.

## Testes e verificações

Execute os testes do app:

```powershell
python manage.py test catalogo
```

Verifique a configuração do projeto e se faltam migrações:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
```

Os testes cobrem operações CRUD, autenticação, filtros, paginação, validações
de preço/código IBGE e funcionamento do Admin. As chamadas externas do IBGE
são simuladas nos testes para que eles não dependam da disponibilidade da
internet.

## Aspectos da implementação

Um dos aspectos relevantes da implementação consiste na integração com um
serviço externo sem tornar o cadastro dependente de sua disponibilidade
contínua. Para isso, foram adotados tempo limite para requisições, cache,
validação de unidades federativas e códigos municipais, além de respostas HTTP
específicas para entradas inválidas, falhas de comunicação e respostas
inconsistentes do serviço. A arquitetura também articula modelos, serializers,
viewsets e routers para disponibilizar operações CRUD com validação e
autenticação.

## Questões do enunciado

As questões referentes à “seção 7” e aos itens “E1 a E4” não constam nos
materiais disponibilizados para a elaboração deste documento. Assim, não são
apresentadas respostas para esses itens.
