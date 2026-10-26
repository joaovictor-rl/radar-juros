from src.load import carregar, conectar
from src.transform import transformar

from tests.test_transform import registro


def test_rodar_duas_vezes_nao_duplica():
    conexao = conectar(":memory:")
    validos, _ = transformar([registro(), registro(cnpj8="87654321", Posicao=2)])

    assert carregar(conexao, validos) == 2
    assert carregar(conexao, validos) == 0


def test_nome_do_banco_fica_o_mais_recente():
    conexao = conectar(":memory:")
    carregar(conexao, transformar([registro()])[0])
    carregar(conexao, transformar([registro(InicioPeriodo="2026-10-02", InstituicaoFinanceira="NOVO NOME S.A.")])[0])

    nome = conexao.execute("SELECT nome FROM instituicoes").fetchone()[0]
    assert nome == "NOVO NOME S.A."
