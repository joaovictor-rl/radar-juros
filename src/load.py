import sqlite3

import pandas as pd

TABELAS = """
CREATE TABLE IF NOT EXISTS instituicoes (
    cnpj8 TEXT PRIMARY KEY,
    nome  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxas (
    inicio_periodo TEXT NOT NULL,
    fim_periodo    TEXT NOT NULL,
    segmento       TEXT NOT NULL,
    modalidade     TEXT NOT NULL,
    cnpj8          TEXT NOT NULL REFERENCES instituicoes (cnpj8),
    posicao        INTEGER,
    taxa_mes       REAL NOT NULL,
    taxa_ano       REAL NOT NULL,
    PRIMARY KEY (inicio_periodo, segmento, modalidade, cnpj8)
);
"""

COLUNAS_TAXAS = [
    "inicio_periodo", "fim_periodo", "segmento", "modalidade",
    "cnpj8", "posicao", "taxa_mes", "taxa_ano",
]


def conectar(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.executescript(TABELAS)
    return conexao


def ultima_data(conexao):
    return conexao.execute("SELECT MAX(inicio_periodo) FROM taxas").fetchone()[0]


def contar_taxas(conexao):
    return conexao.execute("SELECT COUNT(*) FROM taxas").fetchone()[0]


def carregar(conexao, validos):
    antes = contar_taxas(conexao)

    # o nome do banco fica numa tabela separada; se ele mudar de nome, fica o mais recente
    bancos = validos.drop_duplicates("cnpj8", keep="last")[["cnpj8", "banco"]]
    conexao.executemany(
        "INSERT INTO instituicoes (cnpj8, nome) VALUES (?, ?) "
        "ON CONFLICT (cnpj8) DO UPDATE SET nome = excluded.nome",
        bancos.values.tolist(),
    )

    # OR IGNORE: uma taxa que já está no banco (mesma chave) não entra de novo,
    # então rodar o pipeline duas vezes não duplica nada
    conexao.executemany(
        "INSERT OR IGNORE INTO taxas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        validos[COLUNAS_TAXAS].astype(object).values.tolist(),
    )
    conexao.commit()
    return contar_taxas(conexao) - antes


def exportar_csv(conexao, caminho):
    tabela = pd.read_sql(
        """
        SELECT t.inicio_periodo, t.fim_periodo, i.nome AS banco, t.cnpj8,
               t.segmento, t.modalidade, t.posicao, t.taxa_mes, t.taxa_ano
        FROM taxas t
        JOIN instituicoes i ON i.cnpj8 = t.cnpj8
        ORDER BY t.inicio_periodo, t.modalidade, t.posicao
        """,
        conexao,
    )
    # ";" e vírgula decimal: é o formato que o Power BI e o Excel em português leem direto
    tabela.to_csv(caminho, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return len(tabela)
