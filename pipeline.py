import argparse
from datetime import date, timedelta

from src.extract import buscar_taxas
from src.load import carregar, conectar, exportar_csv, ultima_data
from src.transform import transformar

BANCO = "taxas.db"
CSV = "taxas.csv"


def definir_inicio(conexao, desde_informado):
    if desde_informado:
        return date.fromisoformat(desde_informado)
    # carga incremental: na primeira vez busca 1 ano; depois, só os dias que ainda não estão no banco
    ultima = ultima_data(conexao)
    if ultima:
        return date.fromisoformat(ultima) + timedelta(days=1)
    return date.today() - timedelta(days=365)


def main():
    parser = argparse.ArgumentParser(description="Taxas de juros por banco (Banco Central)")
    parser.add_argument("--desde", help="data inicial no formato AAAA-MM-DD (opcional)")
    args = parser.parse_args()

    conexao = conectar(BANCO)
    desde = definir_inicio(conexao, args.desde)
    print(f"Buscando taxas a partir de {desde}...")

    registros = buscar_taxas(desde.isoformat())
    validos, descartados = transformar(registros)
    novas = carregar(conexao, validos)

    print(f"Linhas lidas: {len(registros)}")
    print(f"Linhas válidas: {len(validos)}")
    print(f"Linhas descartadas: {len(descartados)}")
    for motivo, quantidade in descartados["motivo"].value_counts().items():
        print(f"  - {motivo}: {quantidade}")
    print(f"Linhas novas no banco: {novas}")
    print(f"CSV para o Power BI: {exportar_csv(conexao, CSV)} linhas em {CSV}")
    conexao.close()


if __name__ == "__main__":
    main()
