"""Painel público do Radar de Juros (Streamlit).

Lê o banco SQLite gerado pelo pipeline. Se o arquivo não existir localmente,
baixa a versão mais recente publicada pelo GitHub Actions (variável DADOS_URL).
"""
import os
import re
import sqlite3
import urllib.request
from contextlib import closing
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PASTA = Path(__file__).parent
BANCO = PASTA / "juros.db"
DADOS_URL = os.getenv(
    "DADOS_URL",
    "https://github.com/joaovictor-rl/radar-juros/releases/download/dados/juros.db",
)
LIMITE_LINHAS = 5000

# paleta categórica em ordem fixa (cor segue o banco, não a posição)
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
CINZA = "#8a8984"
# divergente: abaixo da mediana (mais barato) x acima (mais caro)
BARATO, CARO = "#2a78d6", "#eb6834"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
# Banco do Brasil, Itaú, Bradesco, Santander, Caixa (cnpj8)
GRANDES = ["00000000", "60701190", "60746948", "90400888", "00360305"]

st.set_page_config(page_title="Radar de Juros", page_icon="📊", layout="wide")

# menos espaço vazio: o Streamlit reserva ~6rem no topo e no rodapé por padrão
st.html("""<style>
.block-container { padding-top: 4.5rem; padding-bottom: 2rem; }  /* 4.5rem: abaixo da barra do Streamlit Cloud */
h1 { padding-top: 0; }
[data-testid="stMetric"] { padding: 0.25rem 0; }
.st-key-resumo [data-testid="stMetric"] { min-width: 140px; }
</style>""")


# ---------------------------------------------------------------- dados

@st.cache_resource(ttl=6 * 3600, show_spinner="Baixando a base mais recente...")
def caminho_do_banco():
    if BANCO.exists() and not os.getenv("SEMPRE_BAIXAR"):
        return str(BANCO)
    destino = Path("/tmp/juros.db")
    urllib.request.urlretrieve(DADOS_URL, destino)
    return str(destino)


def conectar():
    # mode=ro abre o banco só para leitura: qualquer INSERT, UPDATE, DELETE ou DROP dá erro
    return sqlite3.connect(f"file:{caminho_do_banco()}?mode=ro", uri=True, check_same_thread=False)


@st.cache_data(ttl=6 * 3600)
def consultar(sql, parametros=()):
    with closing(conectar()) as conexao:
        return pd.read_sql_query(sql, conexao, params=parametros)


def consulta_livre(sql):
    with closing(conectar()) as conexao:
        cursor = conexao.execute(sql)
        colunas = [c[0] for c in cursor.description or []]
        linhas = cursor.fetchmany(LIMITE_LINHAS + 1)
    cortado = len(linhas) > LIMITE_LINHAS
    return pd.DataFrame(linhas[:LIMITE_LINHAS], columns=colunas), cortado


BASE = """
SELECT t.inicio_periodo, t.fim_periodo, i.nome AS banco, t.cnpj8,
       m.segmento, m.modalidade, t.posicao, t.taxa_mes, t.taxa_ano
FROM taxas t
JOIN instituicoes i ON i.cnpj8 = t.cnpj8
JOIN modalidades m ON m.codigo_segmento = t.codigo_segmento AND m.codigo_modalidade = t.codigo_modalidade
"""


def estilo(fig, **layout):
    """Padrão de legibilidade para todos os gráficos: fontes maiores e separador decimal brasileiro."""
    fig.update_layout(
        separators=",.", font=dict(size=14), hoverlabel=dict(font_size=14),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=13)),
        **layout,
    )
    fig.update_xaxes(tickfont=dict(size=13), title_font=dict(size=13))
    fig.update_yaxes(tickfont=dict(size=13), title_font=dict(size=13))
    return fig


def rotulo_modalidade(segmento, modalidade):
    sigla = "PF" if "FÍSICA" in segmento.upper() else "PJ"
    return f"{sigla} · " + modalidade.replace(" - Prefixado", "").replace(" referenciado em", "")


def nome_curto(nome):
    return re.sub(r"\s+(S\.?A\.?|S/A|LTDA\.?)$", "", nome.replace("BCO ", "BANCO "), flags=re.I).strip()


def pct(valor):
    return f"{valor:.2f}%".replace(".", ",")


# ---------------------------------------------------------------- cabeçalho

modalidades = consultar("SELECT segmento, modalidade FROM modalidades ORDER BY segmento, modalidade")
periodos = consultar("SELECT DISTINCT inicio_periodo, fim_periodo FROM taxas ORDER BY inicio_periodo DESC")
resumo = consultar("SELECT COUNT(*) AS linhas, COUNT(DISTINCT cnpj8) AS bancos FROM taxas").iloc[0]
ultimo = periodos.iloc[0]

st.title("Radar de Juros")
st.caption(
    "Taxas de juros cobradas por cada banco no Brasil, por tipo de crédito. "
    "Fonte: [Banco Central — dados abertos](https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros-de-operacoes-de-credito). "
    f"Período mais recente: {pd.to_datetime(ultimo.inicio_periodo):%d/%m/%Y} a {pd.to_datetime(ultimo.fim_periodo):%d/%m/%Y}."
)
resumo_box = st.container(horizontal=True, wrap=True, gap="large", key="resumo")
c1 = c2 = c3 = c4 = resumo_box
c1.metric("Registros", f"{resumo.linhas:,}".replace(",", "."))
c2.metric("Instituições", int(resumo.bancos))
c3.metric("Modalidades", len(modalidades))
c4.metric("Dias de histórico", len(periodos))


def escolher_modalidade(chave, padrao="Crédito pessoal consignado INSS - Prefixado", colunas=None):
    col1, col2 = colunas or st.columns([1, 3])
    segmentos = sorted(modalidades.segmento.unique())
    seg_padrao = modalidades.loc[modalidades.modalidade == padrao, "segmento"]
    seg_padrao = seg_padrao.iloc[0] if len(seg_padrao) else segmentos[0]
    segmento = col1.selectbox("Segmento", segmentos, index=segmentos.index(seg_padrao), key=f"seg_{chave}")
    opcoes = modalidades.loc[modalidades.segmento == segmento, "modalidade"].tolist()
    modalidade = col2.selectbox(
        "Modalidade", opcoes, index=opcoes.index(padrao) if padrao in opcoes else 0, key=f"mod_{chave}"
    )
    return segmento, modalidade


aba_ranking, aba_evolucao, aba_banco, aba_sql = st.tabs(
    ["Ranking", "Evolução no tempo", "Banco × mercado", "SQL livre"]
)

# ---------------------------------------------------------------- ranking

with aba_ranking:
    st.subheader("Quem cobra mais e quem cobra menos")
    c_seg, c_mod, c_per = st.columns([1, 2.2, 1.2])
    segmento, modalidade = escolher_modalidade("rk", colunas=(c_seg, c_mod))
    rotulos = {
        r.inicio_periodo: f"{pd.to_datetime(r.inicio_periodo):%d/%m/%Y} a {pd.to_datetime(r.fim_periodo):%d/%m/%Y}"
        for r in periodos.itertuples()
    }
    periodo = c_per.selectbox("Período (5 dias úteis)", list(rotulos), format_func=rotulos.get, key="per_rk")
    df = consultar(
        BASE + "WHERE m.segmento = ? AND m.modalidade = ? AND t.inicio_periodo = ? ORDER BY t.taxa_mes",
        (segmento, modalidade, periodo),
    )
    if df.empty:
        st.info("Nenhum banco informou taxa para essa modalidade nesse período. Tente outro período.")
    else:
        df["banco"] = df["banco"].map(nome_curto)
        menor, maior, mediana = df.taxa_mes.min(), df.taxa_mes.max(), df.taxa_mes.median()
        grafico, lateral = st.columns([2.3, 1], gap="large")

        with lateral:
            m1, m2 = st.columns(2)
            m1.metric("Menor taxa", pct(menor))
            m2.metric("Maior taxa", pct(maior))
            m3, m4 = st.columns(2)
            m3.metric("Mediana", pct(mediana))
            m4.metric("Mais caro ÷ mais barato", f"{maior / menor:.1f}×".replace(".", ",") if menor > 0 else "—")
            st.caption(f"Mais barato: **{df.iloc[0].banco}**  \nMais caro: **{df.iloc[-1].banco}**  \n{len(df)} bancos informaram · taxas ao mês")
            # tabela simples (st.table), sem os menus de ordenar/formatar do st.dataframe
            tabela = pd.DataFrame({
                "#": df.posicao.astype(int),
                "Banco": df.banco,
                "%\u00a0a.m.": df.taxa_mes.map(lambda v: f"{v:.2f}".replace(".", ",")),
                "%\u00a0a.a.": df.taxa_ano.map(lambda v: f"{v:.2f}".replace(".", ",")),
            })
            st.table(tabela, hide_index=True, border="horizontal", height=420 if len(df) > 11 else "content")

        with grafico:
            todos = st.toggle(f"Mostrar todos os {len(df)} bancos", value=len(df) <= 25, key="todos_rk")
        vis = df if todos or len(df) <= 20 else pd.concat([df.head(10), df.tail(10)])
        vis = vis.assign(lado=["abaixo" if v < mediana else "acima" for v in vis.taxa_mes])
        extremos = set(vis.head(3).index) | set(vis.tail(3).index)
        vis["texto"] = [pct(v) if i in extremos else "" for i, v in zip(vis.index, vis.taxa_mes)]

        # pontos em vez de barras: o eixo não precisa começar no zero e as diferenças ficam visíveis
        folga = (maior - menor) * 0.12 or 0.1
        fig = go.Figure()
        for lado, cor, nome in [("abaixo", BARATO, "Abaixo da mediana"), ("acima", CARO, "Na mediana ou acima")]:
            parte = vis[vis.lado == lado]
            fig.add_trace(go.Scatter(
                x=parte.taxa_mes, y=parte.banco, mode="markers+text", name=nome,
                text=parte.texto, textposition="middle right", textfont=dict(size=12),
                marker=dict(color=cor, size=12, line=dict(color="rgba(255,255,255,0.9)", width=1.5)),
                customdata=parte[["taxa_ano", "posicao"]],
                hovertemplate="<b>%{y}</b><br>%{x:.2f}% ao mês · %{customdata[0]:.2f}% ao ano<br>posição %{customdata[1]}<extra></extra>",
            ))
        fig.add_vline(x=mediana, line_dash="dash", line_color=CINZA, line_width=1.5)
        estilo(
            fig, height=max(320, 26 * len(vis) + 120), margin=dict(l=0, r=10, t=40, b=10),
            xaxis=dict(title=f"Taxa ao mês · linha tracejada = mediana ({pct(mediana)})", range=[menor - folga, maior + folga * 2.5],
                       ticksuffix="%", tickformat=".2f", nticks=8),
            yaxis=dict(categoryorder="array", categoryarray=vis.banco.tolist()[::-1], title=None, showgrid=True),
        )
        if len(vis) < len(df):
            grafico.caption("Mostrando os 10 mais baratos e os 10 mais caros. Ative a chave acima para ver todos.")
        grafico.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- evolução

with aba_evolucao:
    st.subheader("Como a taxa de cada banco mudou ao longo do ano")
    segmento, modalidade = escolher_modalidade("ev", "Cartão de crédito - rotativo total - Prefixado")
    df = consultar(BASE + "WHERE m.segmento = ? AND m.modalidade = ?", (segmento, modalidade))
    if df.empty:
        st.info("Sem dados para essa modalidade.")
    else:
        df["banco"] = df["banco"].map(nome_curto)
        # o BC publica uma janela móvel de 5 dias úteis por dia; a média semanal tira o ruído
        df["semana"] = pd.to_datetime(df["inicio_periodo"]).dt.to_period("W").dt.start_time
        presentes = dict(zip(df.cnpj8, df.banco))
        padrao = [presentes[c] for c in GRANDES if c in presentes][:4] or df.banco.value_counts().index[:4].tolist()
        escolhidos = st.multiselect(
            "Bancos (até 5)", sorted(df.banco.unique()), default=padrao, max_selections=5, key="bancos_ev"
        )
        mercado = df.groupby("semana", as_index=False).taxa_mes.median()
        # rótulos de mês em português (o Plotly só traz os nomes em inglês)
        meses = pd.date_range(df.semana.min(), df.semana.max(), freq="MS")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=mercado.semana, y=mercado.taxa_mes, name="Mediana do mercado", mode="lines",
            line=dict(color=CINZA, width=2.5, dash="dash"), hovertemplate="%{y:.2f}%<extra>Mediana do mercado</extra>",
        ))
        for cor, banco in zip(CORES, escolhidos):
            serie = df[df.banco == banco].groupby("semana", as_index=False).taxa_mes.mean()
            fig.add_trace(go.Scatter(
                x=serie.semana, y=serie.taxa_mes, name=banco, mode="lines",
                line=dict(color=cor, width=3), hovertemplate=f"%{{y:.2f}}%<extra>{banco}</extra>",
            ))
            if len(serie):
                # valor atual escrito no fim da linha, para não depender só da cor
                fim = serie.iloc[-1]
                fig.add_trace(go.Scatter(
                    x=[fim.semana], y=[fim.taxa_mes], mode="markers+text", showlegend=False, hoverinfo="skip",
                    marker=dict(color=cor, size=9), text=[pct(fim.taxa_mes)], textposition="middle right",
                    textfont=dict(size=13, color=cor),
                ))
        estilo(
            fig, height=520, hovermode="x unified", margin=dict(l=0, r=60, t=50, b=10),
            yaxis=dict(title="Taxa ao mês", ticksuffix="%"),
            xaxis=dict(title=None, tickvals=meses, ticktext=[f"{MESES[m.month - 1]}/{m:%y}" for m in meses]),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("Média semanal de cada banco. A linha tracejada é a mediana de todos os bancos que informaram taxa na semana. O número no fim de cada linha é a taxa da última semana. Falhas na linha: o banco não informou taxa naquela semana.")

# ---------------------------------------------------------------- banco x mercado

with aba_banco:
    st.subheader("Um banco comparado com o resto do mercado")
    bancos = consultar(
        "SELECT i.cnpj8, i.nome, COUNT(*) AS n FROM taxas t JOIN instituicoes i ON i.cnpj8 = t.cnpj8 "
        "WHERE t.inicio_periodo = ? GROUP BY 1, 2 ORDER BY n DESC", (ultimo.inicio_periodo,)
    )
    bancos["rotulo"] = bancos.nome.map(nome_curto)
    escolha = st.selectbox("Banco", bancos.rotulo.tolist(), key="banco_bx")
    cnpj = bancos.loc[bancos.rotulo == escolha, "cnpj8"].iloc[0]
    semana = consultar(BASE + "WHERE t.inicio_periodo = ?", (ultimo.inicio_periodo,))
    stats = semana.groupby(["segmento", "modalidade"]).agg(
        mediana=("taxa_mes", "median"), bancos=("taxa_mes", "size")
    ).reset_index()
    dele = semana[semana.cnpj8 == cnpj].merge(stats, on=["segmento", "modalidade"])
    if dele.empty:
        st.info("Esse banco não informou taxas no período mais recente.")
    else:
        # diferença relativa à mediana: põe consignado (~1,5% a.m.) e rotativo (~15% a.m.) na mesma régua
        dele["diferenca"] = (dele.taxa_mes / dele.mediana - 1) * 100
        dele["rotulo"] = [rotulo_modalidade(sg, md) for sg, md in zip(dele.segmento, dele.modalidade)]
        dele = dele.sort_values("diferenca", ascending=False)
        abaixo = int((dele.diferenca < 0).sum())
        st.caption(
            f"Período mais recente ({pd.to_datetime(ultimo.inicio_periodo):%d/%m/%Y}): **{escolha}** cobra menos que a mediana "
            f"do mercado em **{abaixo} de {len(dele)}** modalidades em que informou taxa."
        )
        fig = go.Figure(go.Bar(
            x=dele.diferenca, y=dele.rotulo, orientation="h",
            marker_color=[BARATO if v < 0 else CARO for v in dele.diferenca],
            text=[f"{v:+.0f}%".replace("+0%", "0%") for v in dele.diferenca], textposition="outside",
            textfont=dict(size=13), cliponaxis=False,
            customdata=dele[["taxa_mes", "mediana", "posicao", "bancos"]],
            hovertemplate=(
                "<b>%{y}</b><br>" + escolha + ": %{customdata[0]:.2f}% ao mês<br>"
                "Mediana do mercado: %{customdata[1]:.2f}%<br>Posição %{customdata[2]} de %{customdata[3]}<extra></extra>"
            ),
        ))
        fig.add_vline(x=0, line_color=CINZA, line_width=1.5)
        limite = max(abs(dele.diferenca).max() * 1.25, 10)
        estilo(
            fig, height=max(320, 30 * len(dele) + 80), margin=dict(l=0, r=20, t=10, b=10), bargap=0.3, showlegend=False,
            xaxis=dict(title="Diferença para a mediana do mercado (← mais barato · mais caro →)", ticksuffix="%",
                       range=[-limite, limite], zeroline=False),
            yaxis=dict(title=None, autorange="reversed"),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("Ex.: −20% = cobra 20% menos que a mediana dos bancos naquela modalidade. Passe o mouse para ver as taxas.")

# ---------------------------------------------------------------- SQL livre

EXEMPLOS = {}
arquivo_sql = PASTA / "sql" / "consultas.sql"
if arquivo_sql.exists():
    for bloco in re.split(r"\n(?=-- )", arquivo_sql.read_text(encoding="utf-8").strip()):
        titulo, _, corpo = bloco.partition("\n")
        if corpo.strip():
            EXEMPLOS[titulo.lstrip("- ").strip()] = corpo.strip()

with aba_sql:
    st.subheader("Escreva sua própria consulta")
    st.caption(
        f"Banco SQLite somente leitura: só consultas `SELECT`, mostrando até {LIMITE_LINHAS:,} linhas.".replace(",", ".")
    )
    with st.expander("Tabelas e colunas"):
        st.markdown(
            "- **taxas** — `inicio_periodo`, `fim_periodo`, `codigo_segmento`, `codigo_modalidade`, `cnpj8`, `posicao`, `taxa_mes`, `taxa_ano`\n"
            "- **instituicoes** — `cnpj8`, `nome`\n"
            "- **modalidades** — `codigo_segmento`, `codigo_modalidade`, `segmento`, `modalidade`\n"
            "- **execucoes** — histórico de cada carga do pipeline\n\n"
            "Junte `taxas` com `instituicoes` por `cnpj8`, e com `modalidades` por "
            "`codigo_segmento` + `codigo_modalidade`."
        )
    nomes = ["(em branco)"] + list(EXEMPLOS)
    exemplo = st.selectbox("Começar de um exemplo", nomes, index=1 if EXEMPLOS else 0)
    texto_inicial = EXEMPLOS.get(exemplo, "SELECT * FROM taxas LIMIT 20;")
    sql = st.text_area("SQL", texto_inicial, height=220, key=f"sql_{exemplo}")
    if st.button("Executar consulta", type="primary"):
        try:
            resultado, cortado = consulta_livre(sql)
        except sqlite3.DatabaseError as erro:
            mensagem = str(erro)
            if "readonly" in mensagem:
                mensagem = "o banco é somente leitura, então só consultas SELECT funcionam aqui."
            elif "one statement" in mensagem:
                mensagem = "rode uma consulta por vez (sem vários comandos separados por ';')."
            st.error(f"Não deu para rodar essa consulta: {mensagem}")
        else:
            st.success(f"{len(resultado)} linhas" + (f" (mostrando só as primeiras {LIMITE_LINHAS})" if cortado else ""))
            st.dataframe(resultado, hide_index=True, width="stretch")
            st.download_button(
                "Baixar CSV", resultado.to_csv(index=False).encode("utf-8"), "consulta.csv", "text/csv"
            )
