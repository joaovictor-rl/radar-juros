from src.transform import transformar


def registro(**alteracoes):
    base = {
        "InicioPeriodo": "2026-10-01",
        "FimPeriodo": "2026-10-07",
        "Segmento": "PESSOA FÍSICA",
        "Modalidade": "Crédito pessoal consignado INSS - Prefixado",
        "Posicao": 1,
        "InstituicaoFinanceira": "BANCO EXEMPLO S.A.",
        "TaxaJurosAoMes": 1.5,
        "TaxaJurosAoAno": 19.56,
        "cnpj8": "12345678",
    }
    base.update(alteracoes)
    return base


def test_registro_correto_e_aceito():
    validos, descartados = transformar([registro()])
    assert len(validos) == 1
    assert descartados.empty


def test_cnpj_curto_e_completado_com_zeros():
    validos, _ = transformar([registro(cnpj8="360305")])
    assert validos.iloc[0]["cnpj8"] == "00360305"


def test_campo_obrigatorio_vazio_e_descartado():
    _, descartados = transformar([registro(InstituicaoFinanceira=None)])
    assert descartados.iloc[0]["motivo"] == "campo obrigatório vazio"


def test_periodo_invertido_e_descartado():
    _, descartados = transformar([registro(FimPeriodo="2026-09-01")])
    assert descartados.iloc[0]["motivo"] == "período inválido"


def test_taxa_negativa_e_descartada():
    _, descartados = transformar([registro(TaxaJurosAoMes=-1)])
    assert descartados.iloc[0]["motivo"] == "taxa negativa"


def test_taxa_zerada_e_descartada():
    # caso real da API: 0,00% ao mês com 0,03% ao ano
    _, descartados = transformar([registro(TaxaJurosAoMes=0, TaxaJurosAoAno=0.03)])
    assert descartados.iloc[0]["motivo"] == "taxa zerada"


def test_cnpj_com_letras_e_descartado():
    _, descartados = transformar([registro(cnpj8="ABC12345")])
    assert descartados.iloc[0]["motivo"] == "CNPJ inválido"


def test_duplicado_mantem_so_o_primeiro():
    validos, descartados = transformar([registro(), registro()])
    assert len(validos) == 1
    assert descartados.iloc[0]["motivo"] == "registro duplicado"
