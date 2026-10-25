import pandas as pd

COLUNAS = {
    "InicioPeriodo": "inicio_periodo",
    "FimPeriodo": "fim_periodo",
    "codigoSegmento": "codigo_segmento",
    "Segmento": "segmento",
    "codigoModalidade": "codigo_modalidade",
    "Modalidade": "modalidade",
    "Posicao": "posicao",
    "InstituicaoFinanceira": "instituicao",
    "TaxaJurosAoMes": "taxa_mes",
    "TaxaJurosAoAno": "taxa_ano",
    "cnpj8": "cnpj8",
}

OBRIGATORIOS = [
    "inicio_periodo", "fim_periodo", "codigo_segmento", "segmento",
    "codigo_modalidade", "modalidade", "cnpj8", "instituicao", "taxa_mes", "taxa_ano",
]

CHAVE = ["inicio_periodo", "codigo_segmento", "codigo_modalidade", "cnpj8"]

TEXTOS = ["codigo_segmento", "segmento", "codigo_modalidade", "modalidade", "instituicao", "cnpj8"]


def _chave_nome(segmento, modalidade):
    return segmento.astype("string").str.strip().str.upper() + "|" + modalidade.astype("string").str.strip()


def completar_codigos(df, parametros):
    """Preenche codigo_segmento/codigo_modalidade vazios a partir da tabela ParametrosConsulta."""
    if not parametros:
        return df
    p = pd.DataFrame(parametros)
    p = p[p.get("tipoModalidade", "D") == "D"]
    p["chave"] = _chave_nome(p["segmento"], p["modalidade"])
    p = p.drop_duplicates("chave")
    chaves = _chave_nome(df["segmento"], df["modalidade"])
    for destino, origem in [("codigo_segmento", "codigoSegmento"), ("codigo_modalidade", "codigoModalidade")]:
        mapa = p.set_index("chave")[origem].astype("string")
        df[destino] = df[destino].fillna(chaves.map(mapa))
    return df


def transformar(registros, parametros=None):
    df = pd.DataFrame(registros, columns=list(COLUNAS)).rename(columns=COLUNAS)

    for coluna in TEXTOS:
        df[coluna] = df[coluna].astype("string").str.strip().replace("", pd.NA)
    df = completar_codigos(df, parametros)
    df["cnpj8"] = df["cnpj8"].str.zfill(8)
    df["inicio_periodo"] = pd.to_datetime(df["inicio_periodo"], errors="coerce")
    df["fim_periodo"] = pd.to_datetime(df["fim_periodo"], errors="coerce")
    df["taxa_mes"] = pd.to_numeric(df["taxa_mes"], errors="coerce")
    df["taxa_ano"] = pd.to_numeric(df["taxa_ano"], errors="coerce")
    df["posicao"] = pd.to_numeric(df["posicao"], errors="coerce").astype("Int64")

    # regras de qualidade: cada linha recebe o primeiro motivo pelo qual falhou
    regras = [
        (df[OBRIGATORIOS].isna().any(axis=1), "campo obrigatório vazio"),
        (df["fim_periodo"] < df["inicio_periodo"], "período inválido"),
        ((df["taxa_mes"] < 0) | (df["taxa_ano"] < 0), "taxa negativa"),
        # 0,00% ao mês não é uma taxa real de crédito: é dado não informado ou arredondado pelo banco
        (df["taxa_mes"] == 0, "taxa zerada"),
        (~df["cnpj8"].str.fullmatch(r"\d{8}").fillna(False).astype(bool), "CNPJ inválido"),
        (df.duplicated(subset=CHAVE, keep="first"), "registro duplicado"),
    ]
    df["motivo_descarte"] = pd.Series(pd.NA, index=df.index, dtype="string")
    for falhou, motivo in regras:
        df.loc[falhou.fillna(False).astype(bool) & df["motivo_descarte"].isna(), "motivo_descarte"] = motivo

    descartados = df[df["motivo_descarte"].notna()].copy()
    validos = df[df["motivo_descarte"].isna()].drop(columns="motivo_descarte").copy()
    validos["inicio_periodo"] = validos["inicio_periodo"].dt.date
    validos["fim_periodo"] = validos["fim_periodo"].dt.date
    return validos, descartados
