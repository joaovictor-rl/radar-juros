import argparse
import os
from datetime import date, timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.extract import buscar_parametros, buscar_taxas
from src.load import carregar, criar_tabelas, exportar_csv, finalizar_execucao, iniciar_execucao, salvar_descartes, ultima_data
from src.transform import transformar


def definir_inicio(engine, desde_informado):
    if desde_informado:
        return date.fromisoformat(desde_informado)
    # carga incremental: na primeira vez busca 1 ano; depois, só o que ainda não está no banco
    ultima = ultima_data(engine)
    if ultima:
        return ultima + timedelta(days=1)
    return date.today() - timedelta(days=365)


def main():
    parser = argparse.ArgumentParser(description="Pipeline das taxas de juros por banco (Banco Central)")
    parser.add_argument("--desde", help="data inicial no formato AAAA-MM-DD (opcional)")
    args = parser.parse_args()

    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///juros.db"))
    criar_tabelas(engine)

    desde = definir_inicio(engine, args.desde)
    print(f"Buscando taxas a partir de {desde}...")
    execucao = iniciar_execucao(engine, desde)

    try:
        registros = buscar_taxas(desde.isoformat())
        validos, descartados = transformar(registros, buscar_parametros())
        novas = carregar(engine, validos)
        salvar_descartes(engine, execucao, descartados)
        finalizar_execucao(engine, execucao, "sucesso", len(registros), len(validos), len(descartados), novas)
    except Exception as erro:
        finalizar_execucao(engine, execucao, "falha", erro=str(erro))
        raise

    print(f"Linhas lidas: {len(registros)}")
    print(f"Linhas válidas: {len(validos)}")
    print(f"Linhas descartadas: {len(descartados)}")
    if not descartados.empty:
        for motivo, quantidade in descartados["motivo_descarte"].value_counts().items():
            print(f"  - {motivo}: {quantidade}")
    print(f"Linhas novas no banco: {novas}")
    print(f"CSV para o Power BI: {exportar_csv(engine, 'taxas.csv')} linhas em taxas.csv")


if __name__ == "__main__":
    main()
