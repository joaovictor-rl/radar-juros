from src.transform import transformar


def registro(**alteracoes):
    base = {
        "InicioPeriodo": "2026-10-01",
        "FimPeriodo": "2026-10-07",
        "codigoSegmento": "1",
        "Segmento": "PESSOA FÍSICA",
        "codigoModalidade": "221101",
        "Modalidade": "Crédito pessoal consignado público - Pré-fixado",
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


def test_taxa_negativa_e_descartada():
    _, descartados = transformar([registro(TaxaJurosAoMes=-1)])
    assert descartados.iloc[0]["motivo_descarte"] == "taxa negativa"


def test_taxa_zerada_e_descartada():
    _, descartados = transformar([registro(TaxaJurosAoMes=0, TaxaJurosAoAno=0)])
    assert descartados.iloc[0]["motivo_descarte"] == "taxa zerada"


def test_taxa_mes_zerada_com_taxa_ano_arredondada_e_descartada():
    # caso real da API: 0,00% a.m. e 0,03% a.a.
    _, descartados = transformar([registro(TaxaJurosAoMes=0, TaxaJurosAoAno=0.03)])
    assert descartados.iloc[0]["motivo_descarte"] == "taxa zerada"


def test_campo_obrigatorio_vazio_e_descartado():
    _, descartados = transformar([registro(InstituicaoFinanceira=None)])
    assert descartados.iloc[0]["motivo_descarte"] == "campo obrigatório vazio"


def test_periodo_invertido_e_descartado():
    _, descartados = transformar([registro(FimPeriodo="2026-09-01")])
    assert descartados.iloc[0]["motivo_descarte"] == "período inválido"


def test_cnpj_com_letras_e_descartado():
    _, descartados = transformar([registro(cnpj8="ABC12345")])
    assert descartados.iloc[0]["motivo_descarte"] == "CNPJ inválido"


def test_duplicado_mantem_so_o_primeiro():
    validos, descartados = transformar([registro(), registro()])
    assert len(validos) == 1
    assert descartados.iloc[0]["motivo_descarte"] == "registro duplicado"


def test_codigos_nulos_sao_preenchidos_pelos_parametros():
    # é assim que a API manda hoje: códigos nulos e segmento em maiúsculas
    parametros = [{
        "codigoSegmento": "1", "segmento": "Pessoa Física", "codigoModalidade": "221101",
        "modalidade": "Crédito pessoal consignado público - Pré-fixado", "tipoModalidade": "D",
    }]
    validos, descartados = transformar([registro(codigoSegmento=None, codigoModalidade=None)], parametros)
    assert descartados.empty
    assert validos.iloc[0]["codigo_segmento"] == "1"
    assert validos.iloc[0]["codigo_modalidade"] == "221101"


def test_modalidade_sem_codigo_conhecido_e_descartada():
    validos, descartados = transformar([registro(codigoSegmento=None, codigoModalidade=None)], [])
    assert validos.empty
    assert descartados.iloc[0]["motivo_descarte"] == "campo obrigatório vazio"
