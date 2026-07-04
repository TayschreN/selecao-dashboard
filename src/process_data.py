"""
Pipeline de processamento de dados - Seleção Brasileira de Futebol
--------------------------------------------------------------------
Le os datasets brutos (results.csv, goalscorers.csv, shootouts.csv) da base
"International football results from 1872 to 2026" e gera datasets limpos
e agregados, prontos para consumo do dashboard Dash e do notebook de EDA.

Saídas em data/processed/:
    brazil_matches.csv      -> todos os jogos do Brasil, com colunas derivadas
    yearly_stats.csv        -> agregados por ano
    competition_stats.csv   -> agregados por tipo de competição
    opponent_stats.csv      -> agregados por adversário (retrospecto)
    top_scorers.csv         -> artilheiros históricos da seleção
    world_cup_editions.csv  -> desempenho do Brasil em cada Copa do Mundo
"""

import pandas as pd
import numpy as np
import os

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUT_DIR = os.path.join(RAW_DIR, "processed")
os.makedirs(OUT_DIR, exist_ok=True)

TEAM = "Brazil"

# Agrupamento de competições em categorias mais legíveis para o dashboard
COMPETITION_GROUPS = {
    "FIFA World Cup": "Copa do Mundo",
    "FIFA World Cup qualification": "Eliminatórias da Copa",
    "Copa América": "Copa América",
    "Confederations Cup": "Copa das Confederações",
    "Friendly": "Amistoso",
}


def group_competition(t: str) -> str:
    return COMPETITION_GROUPS.get(t, "Outros Torneios")


def load_raw():
    results = pd.read_csv(os.path.join(RAW_DIR, "results.csv"), parse_dates=["date"])
    goalscorers = pd.read_csv(os.path.join(RAW_DIR, "goalscorers.csv"))
    shootouts = pd.read_csv(os.path.join(RAW_DIR, "shootouts.csv"))
    return results, goalscorers, shootouts


def build_brazil_matches(results: pd.DataFrame) -> pd.DataFrame:
    bra = results[(results["home_team"] == TEAM) | (results["away_team"] == TEAM)].copy()

    # remove jogos futuros ainda não realizados (placar nulo)
    bra = bra.dropna(subset=["home_score", "away_score"]).copy()
    bra["home_score"] = bra["home_score"].astype(int)
    bra["away_score"] = bra["away_score"].astype(int)

    bra["is_home"] = bra["home_team"] == TEAM
    bra["opponent"] = np.where(bra["is_home"], bra["away_team"], bra["home_team"])
    bra["goals_for"] = np.where(bra["is_home"], bra["home_score"], bra["away_score"])
    bra["goals_against"] = np.where(bra["is_home"], bra["away_score"], bra["home_score"])
    bra["goal_diff"] = bra["goals_for"] - bra["goals_against"]

    def outcome(row):
        if row["goals_for"] > row["goals_against"]:
            return "Vitória"
        if row["goals_for"] < row["goals_against"]:
            return "Derrota"
        return "Empate"

    bra["result"] = bra.apply(outcome, axis=1)
    bra["venue_type"] = np.where(
        bra["neutral"] == True, "Neutro", np.where(bra["is_home"], "Casa", "Fora")
    )
    bra["year"] = bra["date"].dt.year
    bra["decade"] = (bra["year"] // 10) * 10
    bra["competition_group"] = bra["tournament"].apply(group_competition)
    bra["points"] = bra["result"].map({"Vitória": 3, "Empate": 1, "Derrota": 0})

    bra = bra.sort_values("date").reset_index(drop=True)
    cols = [
        "date", "year", "decade", "opponent", "is_home", "venue_type", "city", "country",
        "tournament", "competition_group", "goals_for", "goals_against", "goal_diff",
        "result", "points",
    ]
    return bra[cols]


def build_yearly_stats(bra: pd.DataFrame) -> pd.DataFrame:
    g = bra.groupby("year").agg(
        jogos=("result", "count"),
        vitorias=("result", lambda s: (s == "Vitória").sum()),
        empates=("result", lambda s: (s == "Empate").sum()),
        derrotas=("result", lambda s: (s == "Derrota").sum()),
        gols_pro=("goals_for", "sum"),
        gols_contra=("goals_against", "sum"),
        pontos=("points", "sum"),
    ).reset_index()
    g["saldo_gols"] = g["gols_pro"] - g["gols_contra"]
    g["aproveitamento_pct"] = (g["pontos"] / (g["jogos"] * 3) * 100).round(1)
    return g


def build_competition_stats(bra: pd.DataFrame) -> pd.DataFrame:
    g = bra.groupby("competition_group").agg(
        jogos=("result", "count"),
        vitorias=("result", lambda s: (s == "Vitória").sum()),
        empates=("result", lambda s: (s == "Empate").sum()),
        derrotas=("result", lambda s: (s == "Derrota").sum()),
        gols_pro=("goals_for", "sum"),
        gols_contra=("goals_against", "sum"),
    ).reset_index()
    g["aproveitamento_pct"] = (
        (g["vitorias"] * 3 + g["empates"]) / (g["jogos"] * 3) * 100
    ).round(1)
    return g.sort_values("jogos", ascending=False)


def build_opponent_stats(bra: pd.DataFrame) -> pd.DataFrame:
    g = bra.groupby("opponent").agg(
        jogos=("result", "count"),
        vitorias=("result", lambda s: (s == "Vitória").sum()),
        empates=("result", lambda s: (s == "Empate").sum()),
        derrotas=("result", lambda s: (s == "Derrota").sum()),
        gols_pro=("goals_for", "sum"),
        gols_contra=("goals_against", "sum"),
        ultimo_jogo=("date", "max"),
    ).reset_index()
    g["saldo_gols"] = g["gols_pro"] - g["gols_contra"]
    g["aproveitamento_pct"] = (
        (g["vitorias"] * 3 + g["empates"]) / (g["jogos"] * 3) * 100
    ).round(1)
    return g.sort_values("jogos", ascending=False)


def build_top_scorers() -> pd.DataFrame:
    """
    Tabela de artilheiros históricos da Seleção Brasileira.

    IMPORTANTE: não é derivada de goalscorers.csv. Esse arquivo, embora usado
    no pipeline original, cobre apenas ~47% dos gols marcados pelo Brasil ao
    longo da história (1.084 gols com autor registrado, de um total de 2.314
    gols reais em results.csv) — a cobertura por década varia de 16% a 60%,
    o que gerava um ranking de artilheiros completamente distorcido (ex.:
    Pelé aparecia com 26 gols em vez dos 77 reais).

    Os números abaixo vêm da tabela oficial "Brazil national football team
    records and statistics" (Wikipedia, atualizada em 31/03/2026, que cita
    RSSSF/CBF/FIFA como fontes primárias). Nomes empatados em gols dividem
    a mesma posição no ranking.
    """
    data = [
        (1, "Neymar", 79, 128, "2010–atual"),
        (2, "Pelé", 77, 92, "1957–1971"),
        (3, "Ronaldo", 62, 98, "1994–2011"),
        (4, "Romário", 55, 70, "1987–2005"),
        (5, "Zico", 48, 71, "1976–1986"),
        (6, "Bebeto", 38, 75, "1985–1998"),
        (7, "Rivaldo", 35, 74, "1993–2003"),
        (8, "Jairzinho", 33, 81, "1964–1982"),
        (8, "Ronaldinho", 33, 97, "1999–2013"),
        (10, "Ademir", 32, 39, "1945–1953"),
        (10, "Tostão", 32, 54, "1966–1972"),
    ]
    df = pd.DataFrame(data, columns=["rank", "scorer", "gols", "jogos", "carreira"])
    df["media_por_jogo"] = (df["gols"] / df["jogos"]).round(2)
    return df


def build_world_cup_editions(bra: pd.DataFrame) -> pd.DataFrame:
    wc = bra[bra["competition_group"] == "Copa do Mundo"].copy()

    def edition_year(row):
        # Copas ocorrem no ano do jogo (torneio curto, jun-jul)
        return row["year"]

    wc["edicao"] = wc.apply(edition_year, axis=1)
    g = wc.groupby("edicao").agg(
        jogos=("result", "count"),
        vitorias=("result", lambda s: (s == "Vitória").sum()),
        empates=("result", lambda s: (s == "Empate").sum()),
        derrotas=("result", lambda s: (s == "Derrota").sum()),
        gols_pro=("goals_for", "sum"),
        gols_contra=("goals_against", "sum"),
    ).reset_index()
    g["saldo_gols"] = g["gols_pro"] - g["gols_contra"]
    return g.sort_values("edicao")


def main():
    results, goalscorers, shootouts = load_raw()
    bra = build_brazil_matches(results)

    bra.to_csv(os.path.join(OUT_DIR, "brazil_matches.csv"), index=False)
    build_yearly_stats(bra).to_csv(os.path.join(OUT_DIR, "yearly_stats.csv"), index=False)
    build_competition_stats(bra).to_csv(os.path.join(OUT_DIR, "competition_stats.csv"), index=False)
    build_opponent_stats(bra).to_csv(os.path.join(OUT_DIR, "opponent_stats.csv"), index=False)
    build_top_scorers().to_csv(os.path.join(OUT_DIR, "top_scorers.csv"), index=False)
    build_world_cup_editions(bra).to_csv(os.path.join(OUT_DIR, "world_cup_editions.csv"), index=False)

    # pênaltis
    so = shootouts[(shootouts["home_team"] == TEAM) | (shootouts["away_team"] == TEAM)].copy()
    so["venceu_brasil"] = so["winner"] == TEAM
    so.to_csv(os.path.join(OUT_DIR, "shootouts_brazil.csv"), index=False)

    print(f"Jogos processados: {len(bra)}")
    print(f"Período: {bra['date'].min().date()} até {bra['date'].max().date()}")
    print("Arquivos gerados em", OUT_DIR)


if __name__ == "__main__":
    main()
