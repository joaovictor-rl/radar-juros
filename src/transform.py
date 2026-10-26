import pandas as pd

COLUNAS = {
    "InicioPeriodo": "inicio_periodo",
    "FimPeriodo": "fim_periodo",
    "Segmento": "segmento",
    "Modalidade": "modalidade",
    "Posicao": "posicao",
    "InstituicaoFinanceira": "banco",
    "cnpj8": "cnpj8",
    "TaxaJurosAoMes": "taxa_mes",
    "TaxaJurosAoAno": "taxa_ano",
}

# o que identifica uma linha: o mesmo banco não pode ter duas taxas na mesma modalidade e período
CHAVE = ["inicio_periodo", "segmento", "modalidade", "cnpj8"]


def transformar(registros):
    df = pd.DataFrame(registros, columns=list(COLUNAS)).rename(columns=COLUNAS)

    for coluna in ["segmento", "modalidade", "banco", "cnpj8"]:
        df[coluna] = df[coluna].astype("string").str.strip().replace("", pd.NA)
    df["segmento"] = df["segmento"].str.upper()
    # a API manda o CNPJ sem os zeros da esquerda (o do Banco do Brasil chega como "0")
    df["cnpj8"] = df["cnpj8"].str.zfill(8)
    df["inicio_periodo"] = pd.to_datetime(df["inicio_periodo"], errors="coerce")
    df["fim_periodo"] = pd.to_datetime(df["fim_periodo"], errors="coerce")
    for coluna in ["posicao", "taxa_mes", "taxa_ano"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    regras = [
        (df.isna().any(axis=1), "campo obrigatório vazio"),
        (df["fim_periodo"] < df["inicio_periodo"], "período inválido"),
        ((df["taxa_mes"] < 0) | (df["taxa_ano"] < 0), "taxa negativa"),
        # 0,00% ao mês não existe em crédito de verdade: é dado não informado pelo banco
        (df["taxa_mes"] == 0, "taxa zerada"),
        (~df["cnpj8"].str.fullmatch(r"\d{8}", na=False).astype(bool), "CNPJ inválido"),
        (df.duplicated(subset=CHAVE), "registro duplicado"),
    ]
    # cada linha guarda o motivo da primeira regra em que falhou
    df["motivo"] = None
    for falhou, motivo in regras:
        df.loc[falhou & df["motivo"].isna(), "motivo"] = motivo

    descartados = df[df["motivo"].notna()]
    validos = df[df["motivo"].isna()].drop(columns="motivo").copy()
    validos["inicio_periodo"] = validos["inicio_periodo"].dt.strftime("%Y-%m-%d")
    validos["fim_periodo"] = validos["fim_periodo"].dt.strftime("%Y-%m-%d")
    return validos, descartados
