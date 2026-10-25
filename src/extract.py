from urllib.parse import quote, urlencode

import requests

BASE = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/"
TAMANHO_PAGINA = 10000


def _consultar(entidade, parametros):
    # a API do BC (OData) não aceita "+" como espaço no $filter, que é o padrão do requests;
    # por isso a URL é montada à mão com espaços codificados como %20
    url = BASE + entidade + "?" + urlencode(parametros, quote_via=quote)
    resposta = requests.get(url, timeout=120)
    resposta.raise_for_status()
    return resposta.json()["value"]


def buscar_taxas(desde):
    registros = []
    pular = 0
    while True:
        pagina = _consultar("TaxasJurosDiariaPorInicioPeriodo", {
            "$format": "json",
            "$filter": f"InicioPeriodo ge '{desde}'",
            "$orderby": "InicioPeriodo",
            "$top": TAMANHO_PAGINA,
            "$skip": pular,
        })
        registros.extend(pagina)

        # a API devolve no máximo TAMANHO_PAGINA linhas por vez; uma página menor é a última
        if len(pagina) < TAMANHO_PAGINA:
            return registros
        pular += TAMANHO_PAGINA


def buscar_parametros():
    # a consulta diária vem com codigoSegmento e codigoModalidade nulos;
    # os códigos ficam nesta tabela auxiliar, ligada pelo nome do segmento e da modalidade
    return _consultar("ParametrosConsulta", {"$format": "json"})
