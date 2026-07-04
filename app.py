"""
Painel Histórico da Seleção Brasileira de Futebol (1914-2026)
------------------------------------------------------------------
Dashboard interativo em Dash consumindo dados públicos de todos os jogos
oficiais e amistosos da Seleção Brasileira masculina, desde a estreia em
1914 até a Copa do Mundo de 2026.

Fonte dos dados: International football results from 1872 to 2026
(github.com/martj42/international_results)

Autor: Gabriel — projeto de portfólio em ciência de dados / engenharia de dados.
"""

import os
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table

# ----------------------------------------------------------------------
# Cores e tema (espelham assets/style.css)
# Paleta calibrada para alto contraste contra o fundo verde-escuro:
# evitamos verdes apagados/acinzentados perto do tom de fundo e usamos
# tons bem mais claros e saturados para qualquer elemento de dado.
# ----------------------------------------------------------------------
BG = "#0B1F14"
SURFACE = "#123321"
LINE = "#2E5C3E"
YELLOW = "#FFD400"
WIN = "#3DDC84"      # verde vívido (vitória / casa) — bem mais claro que o fundo
DRAW = "#FFD400"     # ouro (empate)
LOSS = "#FF5C5C"      # coral (derrota / fora)
BLUE = "#5DC3FF"      # azul-céu (neutro / accent secundário)
ORANGE = "#FFA63D"    # âmbar (séries únicas: competições, artilheiros)
PURPLE = "#B98CE8"
TEAL = "#4DE6E6"
TEXT = "#F8F5EA"
TEXT_MUTED = "#A9C7B7"

FONT_FAMILY = "Inter, sans-serif"
CHART_FONT_SIZE = 15

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, color=TEXT, size=CHART_FONT_SIZE),
        colorway=[WIN, YELLOW, BLUE, LOSS, PURPLE, TEAL],
        xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE,
                   tickfont=dict(size=13), title_font=dict(size=14), automargin=True),
        yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE,
                   tickfont=dict(size=13), title_font=dict(size=14), automargin=True),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=13)),
        margin=dict(l=10, r=10, t=40, b=10),
    )
)


TITLE_FONT = dict(family="Barlow Condensed, sans-serif", size=21, color=TEXT)


def chart_title(text):
    return dict(text=f"<b>{text}</b>", font=TITLE_FONT, x=0.02, xanchor="left", y=0.97, yanchor="top")


def graph_config(filename):
    """Config padrão dos gráficos: mode bar enxuta, só com o botão de
    baixar imagem (PNG em alta resolução)."""
    return {
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": [
            "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d",
            "autoScale2d", "resetScale2d", "hoverClosestCartesian",
            "hoverCompareCartesian", "toggleSpikelines", "hoverClosestPie",
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": filename,
            "scale": 3,
        },
    }


# ----------------------------------------------------------------------
# Dados
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")


def load_data():
    bra = pd.read_csv(os.path.join(DATA_DIR, "brazil_matches.csv"), parse_dates=["date"])
    yearly = pd.read_csv(os.path.join(DATA_DIR, "yearly_stats.csv"))
    comp = pd.read_csv(os.path.join(DATA_DIR, "competition_stats.csv"))
    opponents = pd.read_csv(os.path.join(DATA_DIR, "opponent_stats.csv"))
    scorers = pd.read_csv(os.path.join(DATA_DIR, "top_scorers.csv"))
    world_cups = pd.read_csv(os.path.join(DATA_DIR, "world_cup_editions.csv"))
    return bra, yearly, comp, opponents, scorers, world_cups


bra, yearly, comp, opponents, scorers, world_cups = load_data()

TOTAL_JOGOS = len(bra)
TOTAL_V = int((bra["result"] == "Vitória").sum())
TOTAL_E = int((bra["result"] == "Empate").sum())
TOTAL_D = int((bra["result"] == "Derrota").sum())
TOTAL_GP = int(bra["goals_for"].sum())
TOTAL_GC = int(bra["goals_against"].sum())
APROVEITAMENTO = round(bra["points"].sum() / (TOTAL_JOGOS * 3) * 100, 1)
WIN_PCT = round(TOTAL_V / TOTAL_JOGOS * 100, 1)


# ----------------------------------------------------------------------
# Insights calculados dinamicamente a partir dos dados
# ----------------------------------------------------------------------
def compute_insights():
    insights = {}

    # Retrospecto geral
    insights["overall"] = (
        f"O Brasil venceu {WIN_PCT}% dos {TOTAL_JOGOS} jogos disputados desde 1914 "
        f"— isso equivale a vencer cerca de {round(WIN_PCT / 10)} a cada 10 partidas. "
        f"O saldo de gols histórico é de {TOTAL_GP - TOTAL_GC:+d} ({TOTAL_GP} pró, {TOTAL_GC} contra)."
    )

    # Mando de campo
    v = bra.groupby("venue_type").agg(
        jogos=("result", "count"),
        pct=("points", lambda s: round(s.sum() / (len(s) * 3) * 100, 1)),
    ).reindex(["Casa", "Neutro", "Fora"])
    diff = round(v.loc["Casa", "pct"] - v.loc["Fora", "pct"], 1)
    insights["venue"] = (
        f"Jogando em casa, o aproveitamento sobe para {v.loc['Casa', 'pct']}% — "
        f"{diff} pontos percentuais a mais do que fora de casa ({v.loc['Fora', 'pct']}%). "
        f"O fator local é vantagem estatística real, não só impressão de torcedor."
    )

    # Evolução por década (só décadas com amostra razoável)
    dec = bra.groupby("decade").agg(jogos=("result", "count"), pontos=("points", "sum"))
    dec["pct"] = (dec["pontos"] / (dec["jogos"] * 3) * 100).round(1)
    dec = dec[dec["jogos"] >= 10]
    best_dec = dec["pct"].idxmax()
    worst_dec = dec["pct"].idxmin()
    insights["trend"] = (
        f"A década de {int(best_dec)} foi a mais dominante, com {dec.loc[best_dec, 'pct']}% de "
        f"aproveitamento em {int(dec.loc[best_dec, 'jogos'])} jogos. A de {int(worst_dec)} foi a mais "
        f"difícil, com {dec.loc[worst_dec, 'pct']}% — mostrando que nem sempre a seleção viveu a "
        f"fase de ouro que a fama sugere."
    )

    # Competições
    best_comp = comp.loc[comp["aproveitamento_pct"].idxmax()]
    worst_comp = comp.loc[comp["aproveitamento_pct"].idxmin()]
    insights["competitions"] = (
        f"O melhor rendimento é em {best_comp['competition_group']} ({best_comp['aproveitamento_pct']}% "
        f"em {int(best_comp['jogos'])} jogos), enquanto {worst_comp['competition_group']} é onde o Brasil "
        f"mais sofre ({worst_comp['aproveitamento_pct']}%) — o nível do adversário nas competições de "
        f"elite do continente pesa no resultado."
    )

    # Copas do Mundo
    best_wc = world_cups.loc[world_cups["saldo_gols"].idxmax()]
    worst_wc = world_cups.loc[world_cups["saldo_gols"].idxmin()]
    insights["world_cups"] = (
        f"A campanha com maior saldo de gols foi em {int(best_wc['edicao'])} "
        f"({best_wc['saldo_gols']:+.0f}, {int(best_wc['gols_pro'])} gols marcados). A pior foi em "
        f"{int(worst_wc['edicao'])} ({worst_wc['saldo_gols']:+.0f}). A campanha de 2026 já está contabilizada "
        f"até a última partida disputada na base de dados."
    )

    # Adversários
    opp_min = opponents[opponents["jogos"] >= 6]
    best_opp = opp_min.loc[opp_min["aproveitamento_pct"].idxmax()]
    worst_opp = opp_min.loc[opp_min["aproveitamento_pct"].idxmin()]
    arg = opponents[opponents["opponent"] == "Argentina"].iloc[0]
    insights["opponents"] = (
        f"Entre rivais com 6+ jogos, o melhor retrospecto é contra {best_opp['opponent']} "
        f"({best_opp['aproveitamento_pct']}%) e o pior contra {worst_opp['opponent']} "
        f"({worst_opp['aproveitamento_pct']}%). Na maior rivalidade do continente, contra a Argentina, "
        f"o retrospecto é apertado: {int(arg['vitorias'])} vitórias do Brasil, {int(arg['empates'])} empates "
        f"e {int(arg['derrotas'])} vitórias argentinas em {int(arg['jogos'])} jogos."
    )

    # Artilheiros
    top1, top2 = scorers.iloc[0], scorers.iloc[1]
    gap = int(top1["gols"] - top2["gols"])
    n_scorers = len(scorers)
    insights["scorers"] = (
        f"{top1['scorer']} é o maior artilheiro da história da seleção, com {int(top1['gols'])} gols em "
        f"{int(top1['jogos'])} jogos — {gap} à frente de {top2['scorer']} ({int(top2['gols'])} em "
        f"{int(top2['jogos'])} jogos). Neymar superou a marca de Pelé em setembro de 2023, mas está sem "
        f"jogar pela seleção desde então por lesões, então o número está parado. Os {n_scorers} nomes "
        f"deste ranking somados cobrem cerca de 80 anos de futebol, de 1945 a 2023."
    )

    # Forma recente / sequência atual
    recent_desc = bra.sort_values("date", ascending=False)
    first_result = recent_desc.iloc[0]["result"]
    streak = 0
    for r in recent_desc["result"]:
        if r == first_result:
            streak += 1
        else:
            break
    label_map = {"Vitória": "vitórias", "Empate": "empates", "Derrota": "derrotas"}
    last20 = bra.tail(20)
    last20_pct = round(last20["points"].sum() / (len(last20) * 3) * 100, 1)
    insights["recent_form"] = (
        f"A seleção chega embalada: {streak} {label_map[first_result]} seguidas até o último jogo "
        f"registrado na base. Nos últimos 20 jogos, o aproveitamento é de {last20_pct}% "
        f"({int((last20['result'] == 'Vitória').sum())}V-{int((last20['result'] == 'Empate').sum())}E-"
        f"{int((last20['result'] == 'Derrota').sum())}D)."
    )

    return insights


INSIGHTS = compute_insights()


def insight_box(text):
    return html.Div([
        html.Span("💡 Insight", className="insight-label"),
        html.P(text, style={"margin": 0}),
    ], className="insight-box")


# ----------------------------------------------------------------------
# Funções para construir gráficos
# ----------------------------------------------------------------------
def fig_result_donut():
    fig = go.Figure(
        go.Pie(
            labels=["Vitórias", "Empates", "Derrotas"],
            values=[TOTAL_V, TOTAL_E, TOTAL_D],
            hole=0.62,
            marker=dict(colors=[WIN, DRAW, LOSS], line=dict(color=BG, width=3)),
            textinfo="label+percent",
            textfont=dict(size=15, color="#0B1F14"),
            sort=False,
        )
    )
    fig.add_annotation(
        text=f"<b>{APROVEITAMENTO}%</b><br><span style='font-size:12px'>aproveitamento</span>",
        showarrow=False,
        font=dict(size=30, color=TEXT),
    )
    fig.update_layout(template=PLOTLY_TEMPLATE, showlegend=False, height=460,
                       title=chart_title("Retrospecto Histórico da Seleção (1914-2026)"),
                       margin=dict(l=10, r=10, t=70, b=10))
    return fig


def fig_yearly_trend():
    y = yearly.copy()
    y["media_movel"] = y["aproveitamento_pct"].rolling(5, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=y["year"], y=y["aproveitamento_pct"], mode="lines", name="Aproveitamento anual",
        line=dict(color=TEXT_MUTED, width=1.2), opacity=0.55,
    ))
    fig.add_trace(go.Scatter(
        x=y["year"], y=y["media_movel"], mode="lines", name="Média móvel (5 anos)",
        line=dict(color=YELLOW, width=3.5),
    ))
    fig.add_hline(y=APROVEITAMENTO, line_dash="dot", line_color=BLUE, line_width=2,
                  annotation_text=f"média histórica {APROVEITAMENTO}%",
                  annotation_font_color=BLUE, annotation_font_size=13)
    fig.update_layout(template=PLOTLY_TEMPLATE, height=500,
                       title=chart_title("Evolução do Aproveitamento por Ano"),
                       legend=dict(orientation="h", y=1.1),
                       margin=dict(l=60, r=10, t=90, b=50),
                       yaxis_title="Aproveitamento (%)")
    return fig


def fig_venue_split():
    v = bra.groupby("venue_type").agg(
        jogos=("result", "count"),
        aproveitamento=("points", lambda s: round(s.sum() / (len(s) * 3) * 100, 1)),
    ).reindex(["Casa", "Neutro", "Fora"]).reset_index()
    fig = go.Figure(go.Bar(
        x=v["venue_type"], y=v["aproveitamento"],
        text=[f"{x}%" for x in v["aproveitamento"]], textposition="outside",
        textfont=dict(size=17, color=TEXT),
        marker_color=[WIN, BLUE, LOSS],
    ))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=460,
                       title=chart_title("Aproveitamento por Mando de Campo"),
                       margin=dict(l=60, r=10, t=70, b=50),
                       yaxis_title="Aproveitamento (%)", yaxis_range=[0, 100])
    return fig


def fig_competition_bar():
    c = comp.sort_values("aproveitamento_pct")
    fig = go.Figure(go.Bar(
        y=c["competition_group"], x=c["aproveitamento_pct"], orientation="h",
        text=[f"{x}%  ({j} jogos)" for x, j in zip(c["aproveitamento_pct"], c["jogos"])],
        textposition="outside",
        textfont=dict(size=14, color=TEXT),
        marker_color=ORANGE,
    ))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=460,
                       title=chart_title("Aproveitamento por Competição"),
                       xaxis_title="Aproveitamento (%)",
                       xaxis_range=[0, 100], margin=dict(l=140, r=110, t=70, b=55))
    return fig


def fig_top_opponents(n=12):
    o = opponents[opponents["jogos"] >= 6].sort_values("jogos", ascending=False).head(n)
    o = o.sort_values("jogos")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=o["opponent"], x=o["vitorias"], name="Vitórias", orientation="h", marker_color=WIN))
    fig.add_trace(go.Bar(y=o["opponent"], x=o["empates"], name="Empates", orientation="h", marker_color=DRAW))
    fig.add_trace(go.Bar(y=o["opponent"], x=o["derrotas"], name="Derrotas", orientation="h", marker_color=LOSS))
    fig.update_layout(template=PLOTLY_TEMPLATE, barmode="stack", height=580,
                       title=chart_title("Retrospecto contra os Principais Adversários"),
                       legend=dict(orientation="h", y=1.05),
                       margin=dict(l=10, r=10, t=90, b=10))
    return fig


def fig_scorers(n=11):
    s = scorers.head(n).sort_values("gols")
    fig = go.Figure(go.Bar(
        y=s["scorer"], x=s["gols"], orientation="h",
        text=s["gols"], textposition="outside",
        textfont=dict(size=14, color=TEXT),
        marker_color=ORANGE,
        marker_line_color=TEXT, marker_line_width=1,
    ))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=500,
                       title=chart_title("Maiores Artilheiros da Seleção Brasileira"),
                       margin=dict(l=10, r=50, t=70, b=10))
    return fig


def fig_world_cups():
    w = world_cups.copy()
    colors = [WIN if x >= 0 else LOSS for x in w["saldo_gols"]]
    fig = go.Figure(go.Bar(
        x=w["edicao"].astype(str), y=w["saldo_gols"], marker_color=colors,
        text=w["saldo_gols"], textposition="outside",
        textfont=dict(size=13, color=TEXT),
    ))
    fig.add_hline(y=0, line_color=LINE, line_width=1.5)
    fig.update_layout(template=PLOTLY_TEMPLATE, height=460,
                       title=chart_title("Saldo de Gols por Edição de Copa do Mundo"),
                       margin=dict(l=60, r=10, t=70, b=60),
                       yaxis_title="Saldo de gols", xaxis_title="Edição da Copa do Mundo")
    return fig


def fig_h2h(opponent):
    row = opponents[opponents["opponent"] == opponent].iloc[0]
    fig = go.Figure(go.Bar(
        x=["Vitórias", "Empates", "Derrotas"],
        y=[row["vitorias"], row["empates"], row["derrotas"]],
        marker_color=[WIN, DRAW, LOSS],
        text=[row["vitorias"], row["empates"], row["derrotas"]],
        textposition="outside",
        textfont=dict(size=16, color=TEXT),
    ))
    fig.update_layout(template=PLOTLY_TEMPLATE, height=400,
                       title=chart_title(f"Brasil x {opponent} — Confronto Direto"),
                       margin=dict(l=10, r=10, t=70, b=10))
    return fig


DARK_TABLE_STYLE = dict(
    style_header={
        "backgroundColor": "#0E241A", "color": TEXT_MUTED, "fontFamily": "JetBrains Mono, monospace",
        "fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.06em",
        "border": f"1px solid {LINE}",
    },
    style_cell={
        "backgroundColor": SURFACE, "color": TEXT, "border": f"1px solid {LINE}",
        "fontFamily": "Inter, sans-serif", "fontSize": "13.5px", "padding": "8px 10px",
        "textAlign": "left",
    },
    style_data_conditional=[
        {"if": {"filter_query": '{Resultado} = "Vitória"'}, "borderLeft": f"3px solid {WIN}"},
        {"if": {"filter_query": '{Resultado} = "Empate"'}, "borderLeft": f"3px solid {DRAW}"},
        {"if": {"filter_query": '{Resultado} = "Derrota"'}, "borderLeft": f"3px solid {LOSS}"},
    ],
    style_table={"overflowX": "auto"},
)


# ----------------------------------------------------------------------
# Componentes de layout
# ----------------------------------------------------------------------
def kpi_tile(value, label, accent=""):
    return html.Div([
        html.Div(value, className="kpi-value"),
        html.Div(label, className="kpi-label"),
    ], className=f"kpi-tile {accent}")


def header():
    return html.Div([
        html.Div([
            html.P("Painel de dados · Futebol", className="eyebrow"),
            html.H1("Seleção Brasileira", className="title"),
            html.P(
                "Retrospecto histórico da Seleção Brasileira masculina (1914-2026): "
                "1.063 jogos oficiais e amistosos, artilheiros, adversários e a campanha "
                "da Copa do Mundo de 2026.",
                className="subtitle"
            ),
        ], className="header-row"),

        html.Div([
            kpi_tile(f"{TOTAL_JOGOS:,}".replace(",", "."), "Jogos"),
            kpi_tile(TOTAL_V, "Vitórias", "accent-win"),
            kpi_tile(TOTAL_E, "Empates"),
            kpi_tile(TOTAL_D, "Derrotas", "accent-loss"),
            kpi_tile(f"{APROVEITAMENTO}%", "Aproveitamento", "accent-blue"),
            kpi_tile(f"{TOTAL_GP}-{TOTAL_GC}", "Gols (pró-contra)"),
        ], className="kpi-row"),
    ])


def tab_visao_geral():
    return html.Div([
        html.Div([
            html.Div([
                html.H3("Retrospecto histórico", className="panel-title"),
                html.P("Distribuição de resultados em 112 anos de seleção.", className="panel-desc"),
                dcc.Graph(figure=fig_result_donut(), config=graph_config("retrospecto_historico")),
                insight_box(INSIGHTS["overall"]),
            ], className="panel"),
            html.Div([
                html.H3("Aproveitamento por mando de campo", className="panel-title"),
                html.P("Jogar em casa segue sendo vantagem estatística real.", className="panel-desc"),
                dcc.Graph(figure=fig_venue_split(), config=graph_config("aproveitamento_mando_campo")),
                insight_box(INSIGHTS["venue"]),
            ], className="panel"),
        ], className="grid-2"),

        html.Div([
            html.H3("Evolução do aproveitamento (1914-2026)", className="panel-title"),
            html.P("Aproveitamento de pontos por ano, com média móvel de 5 anos.", className="panel-desc"),
            dcc.Graph(figure=fig_yearly_trend(), config=graph_config("evolucao_aproveitamento")),
            insight_box(INSIGHTS["trend"]),
        ], className="panel"),
    ])


def tab_competicoes():
    return html.Div([
        html.Div([
            html.H3("Aproveitamento por competição", className="panel-title"),
            html.P("Copa do Mundo, Copa América, Eliminatórias, Amistosos e outros torneios.",
                   className="panel-desc"),
            dcc.Graph(figure=fig_competition_bar(), config=graph_config("aproveitamento_por_competicao")),
            insight_box(INSIGHTS["competitions"]),
        ], className="panel"),

        html.Div([
            html.H3("Copa do Mundo — edição por edição", className="panel-title"),
            html.P("Saldo de gols do Brasil em cada Copa disputada (2026 em andamento).",
                   className="panel-desc"),
            dcc.Graph(figure=fig_world_cups(), config=graph_config("copas_do_mundo_saldo_gols")),
            insight_box(INSIGHTS["world_cups"]),
            dash_table.DataTable(
                data=world_cups.rename(columns={
                    "edicao": "Ano", "jogos": "Jogos", "vitorias": "V", "empates": "E",
                    "derrotas": "D", "gols_pro": "GP", "gols_contra": "GC", "saldo_gols": "SG",
                }).to_dict("records"),
                columns=[{"name": c, "id": c} for c in
                         ["Ano", "Jogos", "V", "E", "D", "GP", "GC", "SG"]],
                page_size=12, **DARK_TABLE_STYLE,
            ),
        ], className="panel"),
    ])


def tab_adversarios():
    top_opp_list = opponents[opponents["jogos"] >= 3].sort_values("jogos", ascending=False)["opponent"].tolist()
    return html.Div([
        html.Div([
            html.H3("Retrospecto contra os maiores rivais", className="panel-title"),
            html.P("Adversários com 6 ou mais jogos disputados contra o Brasil.", className="panel-desc"),
            dcc.Graph(figure=fig_top_opponents(), config=graph_config("retrospecto_adversarios")),
            insight_box(INSIGHTS["opponents"]),
        ], className="panel"),

        html.Div([
            html.H3("Confronto direto (head-to-head)", className="panel-title"),
            html.P("Selecione um adversário para ver o retrospecto completo.", className="panel-desc"),
            html.Label("Adversário", className="control-label"),
            dcc.Dropdown(
                id="opponent-dropdown",
                options=[{"label": o, "value": o} for o in top_opp_list],
                value="Argentina",
                clearable=False,
                style={"color": "#0B1F14"},
            ),
            html.Div(id="h2h-content"),
        ], className="panel"),
    ])


def tab_artilheiros():
    return html.Div([
        html.Div([
            html.H3("Maiores artilheiros da história", className="panel-title"),
            html.P("Ranking oficial (Wikipedia/RSSSF, atualizado em 2026) — não usa o dataset de "
                   "artilheiros por partida, que está incompleto para o Brasil.",
                   className="panel-desc"),
            dcc.Graph(figure=fig_scorers(), config=graph_config("maiores_artilheiros")),
            insight_box(INSIGHTS["scorers"]),
        ], className="panel"),
    ])


def tab_forma_recente():
    recent = bra.tail(25).sort_values("date", ascending=False).copy()
    recent["Data"] = recent["date"].dt.strftime("%d/%m/%Y")
    recent = recent.rename(columns={
        "opponent": "Adversário", "goals_for": "Gols BRA", "goals_against": "Gols Adv",
        "result": "Resultado", "competition_group": "Competição",
    })
    table_cols = ["Data", "Adversário", "Gols BRA", "Gols Adv", "Resultado", "Competição"]
    return html.Div([
        html.Div([
            html.H3("Forma recente — últimos 25 jogos", className="panel-title"),
            html.P("Resultados mais recentes da Seleção, incluindo a Copa de 2026.",
                   className="panel-desc"),
            insight_box(INSIGHTS["recent_form"]),
            dash_table.DataTable(
                data=recent[table_cols].to_dict("records"),
                columns=[{"name": c, "id": c} for c in table_cols],
                page_size=25, **DARK_TABLE_STYLE,
            ),
        ], className="panel"),
    ])


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
app = Dash(__name__, title="Seleção Brasileira — Painel de Dados")
server = app.server  # necessário para deploy no Render (gunicorn app:server)

app.layout = html.Div([
    html.Div([
        header(),
        dcc.Tabs(
            id="tabs",
            value="visao_geral",
            className="dash-tabs",
            children=[
                dcc.Tab(label="Visão Geral", value="visao_geral", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Competições", value="competicoes", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Adversários", value="adversarios", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Artilheiros", value="artilheiros", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Forma Recente", value="forma_recente", className="tab", selected_className="tab--selected"),
            ],
        ),
        html.Div(id="tab-content"),
        html.Footer([
            "Dados: ",
            html.A("martj42/international_results", href="https://github.com/martj42/international_results", target="_blank"),
            " · Projeto de portfólio em dados por Gabriel · Atualizado até jul/2026",
        ], className="credits"),
    ], className="app-shell")
])


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):
    return {
        "visao_geral": tab_visao_geral,
        "competicoes": tab_competicoes,
        "adversarios": tab_adversarios,
        "artilheiros": tab_artilheiros,
        "forma_recente": tab_forma_recente,
    }.get(tab, tab_visao_geral)()


@app.callback(Output("h2h-content", "children"), Input("opponent-dropdown", "value"))
def update_h2h(opponent_name):
    row = opponents[opponents["opponent"] == opponent_name].iloc[0]
    scoreline = html.Div([
        html.Div([html.Div(int(row["vitorias"]), className="h2h-num", style={"color": WIN}), "Vitórias BRA"]),
        html.Div([html.Div(int(row["empates"]), className="h2h-num", style={"color": DRAW}), "Empates"]),
        html.Div([html.Div(int(row["derrotas"]), className="h2h-num", style={"color": LOSS}), f"Vitórias {opponent_name}"]),
    ], className="h2h-scoreline")
    meta = html.P(
        f"{int(row['jogos'])} jogos · gols {int(row['gols_pro'])}-{int(row['gols_contra'])} "
        f"(saldo {int(row['saldo_gols']):+d}) · aproveitamento {row['aproveitamento_pct']}% · "
        f"último jogo em {pd.to_datetime(row['ultimo_jogo']).strftime('%d/%m/%Y')}",
        className="panel-desc", style={"textAlign": "center"}
    )
    return html.Div([
        scoreline, meta,
        dcc.Graph(figure=fig_h2h(opponent_name),
                  config=graph_config(f"confronto_direto_{opponent_name.lower().replace(' ', '_')}")),
    ])


if __name__ == "__main__":
    debug_mode = os.environ.get("DASH_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)