import requests
from django.core.cache import cache


IBGE_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
IBGE_MUNICIPIOS_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/"
    "{uf}/municipios"
)
IBGE_MUNICIPIO_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{codigo}"
)
CACHE_TTL_SECONDS = 60 * 60 * 24
REQUEST_TIMEOUT_SECONDS = 10


class IBGEUnavailable(Exception):
    pass


class IBGEInvalidResponse(Exception):
    pass


def _json_response(response):
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise IBGEInvalidResponse(
            "A API do IBGE retornou uma resposta que não é JSON válido."
        ) from exc


def buscar_municipios(uf):
    uf = uf.upper()
    if uf not in IBGE_UFS:
        raise ValueError("Informe uma sigla válida de estado brasileiro.")

    cache_key = f"ibge_municipios_{uf}"
    municipios = cache.get(cache_key)
    if municipios is not None:
        return municipios

    try:
        response = requests.get(
            IBGE_MUNICIPIOS_URL.format(uf=uf),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IBGEUnavailable(
            "O IBGE está indisponível ou demorou para responder. Tente novamente."
        ) from exc

    data = _json_response(response)
    if not isinstance(data, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), int)
        or not isinstance(item.get("nome"), str)
        for item in data
    ):
        raise IBGEInvalidResponse(
            "A API do IBGE retornou dados de municípios em formato inválido."
        )

    municipios = [
        {"codigo_ibge": item["id"], "nome": item["nome"]}
        for item in data
    ]
    cache.set(cache_key, municipios, CACHE_TTL_SECONDS)
    return municipios


def codigo_municipio_existe(codigo_ibge):
    cache_key = f"ibge_municipio_existe_{codigo_ibge}"
    existe = cache.get(cache_key)
    if existe is not None:
        return existe

    try:
        response = requests.get(
            IBGE_MUNICIPIO_URL.format(codigo=codigo_ibge),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise IBGEUnavailable(
            "O IBGE está indisponível ou demorou para responder. Tente novamente."
        ) from exc

    if response.status_code == 404:
        cache.set(cache_key, False, CACHE_TTL_SECONDS)
        return False

    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IBGEUnavailable(
            "O IBGE está indisponível ou demorou para responder. Tente novamente."
        ) from exc

    data = _json_response(response)
    if (
        not isinstance(data, dict)
        or data.get("id") != codigo_ibge
        or not isinstance(data.get("nome"), str)
    ):
        raise IBGEInvalidResponse(
            "A API do IBGE retornou dados de município em formato inválido."
        )

    cache.set(cache_key, True, CACHE_TTL_SECONDS)
    return True
