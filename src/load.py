import json

import pandas as pd
from datetime import datetime

from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer,
    MetaData, String, Table, Text, func, insert, select, update,
)
from sqlalchemy.dialects.postgresql import insert as insert_postgres
from sqlalchemy.dialects.sqlite import insert as insert_sqlite

metadata = MetaData()

instituicoes = Table(
    "instituicoes", metadata,
    Column("cnpj8", String(8), primary_key=True),
    Column("nome", Text, nullable=False),
)

modalidades = Table(
    "modalidades", metadata,
    Column("codigo_segmento", String(20), primary_key=True),
    Column("codigo_modalidade", String(20), primary_key=True),
    Column("segmento", Text, nullable=False),
    Column("modalidade", Text, nullable=False),
)

taxas = Table(
    "taxas", metadata,
    Column("inicio_periodo", Date, primary_key=True),
    Column("codigo_segmento", String(20), primary_key=True),
    Column("codigo_modalidade", String(20), primary_key=True),
    Column("cnpj8", String(8), ForeignKey("instituicoes.cnpj8"), primary_key=True),
    Column("fim_periodo", Date, nullable=False),
    Column("posicao", Integer),
    Column("taxa_mes", Float, nullable=False),
    Column("taxa_ano", Float, nullable=False),
    ForeignKeyConstraint(
        ["codigo_segmento", "codigo_modalidade"],
        ["modalidades.codigo_segmento", "modalidades.codigo_modalidade"],
    ),
)

execucoes = Table(
    "execucoes", metadata,
    Column("id", Integer, primary_key=True),
    Column("iniciada_em", DateTime, nullable=False),
    Column("finalizada_em", DateTime),
    Column("desde", Date, nullable=False),
    Column("linhas_lidas", Integer),
    Column("linhas_validas", Integer),
    Column("linhas_descartadas", Integer),
    Column("linhas_novas", Integer),
    Column("status", String(20), nullable=False),
    Column("erro", Text),
)

descartes = Table(
    "descartes", metadata,
    Column("id", Integer, primary_key=True),
    Column("execucao_id", Integer, ForeignKey("execucoes.id"), nullable=False),
    Column("motivo", Text, nullable=False),
    Column("registro", Text, nullable=False),
)


def criar_tabelas(engine):
    metadata.create_all(engine)


def _linhas(df):
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _insert(conexao, tabela):
    if conexao.dialect.name == "postgresql":
        return insert_postgres(tabela)
    return insert_sqlite(tabela)


def ultima_data(engine):
    with engine.connect() as conexao:
        return conexao.execute(select(func.max(taxas.c.inicio_periodo))).scalar()


def contar_taxas(conexao):
    return conexao.execute(select(func.count()).select_from(taxas)).scalar()


def carregar(engine, validos):
    if validos.empty:
        return 0

    bancos = (
        validos[["cnpj8", "instituicao"]]
        .drop_duplicates("cnpj8", keep="last")
        .rename(columns={"instituicao": "nome"})
    )
    tipos = validos[["codigo_segmento", "codigo_modalidade", "segmento", "modalidade"]].drop_duplicates(
        ["codigo_segmento", "codigo_modalidade"], keep="last"
    )
    linhas_taxas = validos.drop(columns=["instituicao", "segmento", "modalidade"])

    with engine.begin() as conexao:
        antes = contar_taxas(conexao)

        comando = _insert(conexao, instituicoes)
        # se o banco mudou de nome, fica o nome mais recente
        comando = comando.on_conflict_do_update(index_elements=["cnpj8"], set_={"nome": comando.excluded.nome})
        conexao.execute(comando, _linhas(bancos))

        comando = _insert(conexao, modalidades)
        comando = comando.on_conflict_do_update(
            index_elements=["codigo_segmento", "codigo_modalidade"],
            set_={"segmento": comando.excluded.segmento, "modalidade": comando.excluded.modalidade},
        )
        conexao.execute(comando, _linhas(tipos))

        # períodos que já estão no banco são ignorados, então rodar duas vezes não duplica nada
        conexao.execute(_insert(conexao, taxas).on_conflict_do_nothing(), _linhas(linhas_taxas))

        return contar_taxas(conexao) - antes


def iniciar_execucao(engine, desde):
    with engine.begin() as conexao:
        resultado = conexao.execute(
            insert(execucoes).values(iniciada_em=datetime.now(), desde=desde, status="em andamento")
        )
        return resultado.inserted_primary_key[0]


def finalizar_execucao(engine, execucao_id, status, lidas=None, validas=None, descartadas=None, novas=None, erro=None):
    with engine.begin() as conexao:
        conexao.execute(
            update(execucoes)
            .where(execucoes.c.id == execucao_id)
            .values(
                finalizada_em=datetime.now(), status=status, linhas_lidas=lidas, linhas_validas=validas,
                linhas_descartadas=descartadas, linhas_novas=novas, erro=erro,
            )
        )


def salvar_descartes(engine, execucao_id, descartados):
    if descartados.empty:
        return
    linhas = [
        {
            "execucao_id": execucao_id,
            "motivo": registro.pop("motivo_descarte"),
            "registro": json.dumps(registro, default=str, ensure_ascii=False),
        }
        for registro in _linhas(descartados)
    ]
    with engine.begin() as conexao:
        conexao.execute(insert(descartes), linhas)


def exportar_csv(engine, caminho):
    consulta = (
        select(
            taxas.c.inicio_periodo, taxas.c.fim_periodo, instituicoes.c.nome.label("banco"), taxas.c.cnpj8,
            modalidades.c.segmento, modalidades.c.modalidade, taxas.c.posicao, taxas.c.taxa_mes, taxas.c.taxa_ano,
        )
        .join(instituicoes, instituicoes.c.cnpj8 == taxas.c.cnpj8)
        .join(modalidades, (modalidades.c.codigo_segmento == taxas.c.codigo_segmento)
              & (modalidades.c.codigo_modalidade == taxas.c.codigo_modalidade))
        .order_by(taxas.c.inicio_periodo, modalidades.c.modalidade, taxas.c.posicao)
    )
    with engine.connect() as conexao:
        tabela = pd.read_sql(consulta, conexao)
    # formato brasileiro (";" e vírgula decimal) para o Power BI em português ler os números certo
    tabela.to_csv(caminho, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return len(tabela)
