import requests

URL = "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/TaxasJurosDiariaPorInicioPeriodo"
POR_PAGINA = 10000


def buscar_taxas(desde):
    registros = []
    pular = 0
    while True:
        # a API do BC não aceita "+" no lugar de espaço no filtro, por isso a URL é montada com %20
        url = (
            f"{URL}?$format=json"
            f"&$filter=InicioPeriodo%20ge%20%27{desde}%27"
            f"&$orderby=InicioPeriodo&$top={POR_PAGINA}&$skip={pular}"
        )
        resposta = requests.get(url, timeout=120)
        resposta.raise_for_status()
        pagina = resposta.json()["value"]
        registros.extend(pagina)

        # a API devolve no máximo 10 mil linhas por vez; quando vem menos, era a última página
        if len(pagina) < POR_PAGINA:
            return registros
        pular += POR_PAGINA
