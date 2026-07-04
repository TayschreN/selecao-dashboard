# ⚽ Seleção Brasileira — Painel Histórico de Dados (1914-2026)

Dashboard interativo sobre a Seleção Brasileira de Futebol masculina, cobrindo **1.063 jogos oficiais e amistosos** desde a estreia em 1914 até a Copa do Mundo de 2026 (em andamento na data de corte dos dados).

🔗 **Fonte dos dados (jogos):** [International football results from 1872 to 2026](https://github.com/martj42/international_results)
🔗 **Fonte dos dados (artilheiros):** [Brazil national football team records and statistics — Wikipedia](https://en.wikipedia.org/wiki/Brazil_national_football_team_records_and_statistics) (atualizado em 2026, cita RSSSF/CBF/FIFA)

## ⚠️ Nota sobre qualidade de dados

O dataset público usado para os jogos (`results.csv`) tem um arquivo complementar de artilheiros por partida (`goalscorers.csv`) que é **gravemente incompleto para o Brasil**: cobre apenas ~47% dos 2.314 gols reais marcados pela seleção (a cobertura varia de 16% a 60% por década). Usar esse arquivo direto gerava um ranking de artilheiros completamente errado — por exemplo, mostrava Pelé com 26 gols em vez dos 77 reais, e Ronaldo com 39 em vez de 62.

Por isso, o ranking de artilheiros (`build_top_scorers()` em `src/process_data.py`) **não** usa esse arquivo. Os números vêm da tabela oficial da Wikipédia, verificada manualmente. Os demais dados (jogos, competições, adversários, Copas do Mundo) vêm de `results.csv`, que foi validado contra a Wikipédia em vários pontos — resultados históricos marcantes (Maracanaço, 7x1 vs Alemanha, finais de Copa) e o retrospecto completo contra a Argentina (43V-26E, batendo exato) — e está de acordo com a fonte oficial, com uma diferença mínima e conhecida (~1 jogo a menos no total histórico, por divergência documentada entre AFA e CBF sobre um jogo específico).

## O que o projeto entrega

1. **Pipeline de dados** (`src/process_data.py`): filtra os 1.063 jogos do Brasil na base pública de resultados internacionais e gera datasets agregados (por ano, competição, adversário, edição de Copa) + tabela de artilheiros verificada manualmente.
2. **Dashboard interativo em Dash** (`app.py`): 5 abas — Visão Geral, Competições, Adversários (com dropdown de confronto direto), Artilheiros, Forma Recente — com insights calculados dinamicamente a partir dos dados e botão de download de imagem (PNG em alta resolução) em cada gráfico.
3. **Identidade visual própria** (`assets/style.css`): tema escuro com cores do CBF calibradas para contraste (nada de verde apagado sobre fundo verde), tipografia estilo placar de estádio.

## Stack técnica

- **Python** · pandas para processamento e agregação
- **Dash + Plotly** para o dashboard interativo
- **Gunicorn** como servidor WSGI de produção
- **Render** para deploy (config incluída: `Procfile`, `render.yaml`, `runtime.txt`)

## Estrutura do projeto

```
selecao/
├── app.py                          # Dashboard Dash (ponto de entrada)
├── requirements.txt
├── Procfile                        # gunicorn app:server
├── render.yaml                     # deploy 1-click no Render
├── runtime.txt
├── assets/
│   └── style.css                   # tema visual (identidade CBF: verde/amarelo/azul)
├── src/
│   └── process_data.py             # pipeline de limpeza, agregação e tabela de artilheiros
└── data/
    ├── results.csv                 # dados brutos (todas as seleções)
    ├── goalscorers.csv             # mantido para referência, NÃO usado (incompleto p/ Brasil)
    ├── shootouts.csv
    └── processed/                  # datasets limpos e agregados (gerados pelo pipeline)
```

## Como rodar localmente

```bash
# 1. Criar ambiente e instalar dependências
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. (Re)gerar os datasets processados, se necessário
python src/process_data.py

# 3. Rodar o dashboard
python app.py
# abrir http://localhost:8050
```

## Deploy no Render

1. Suba este repositório no GitHub.
2. No Render, crie um **Web Service** apontando para o repositório (o `render.yaml` já define build/start commands automaticamente).
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:server`

## Principais achados

- Aproveitamento histórico geral: **63,5%** de vitórias (1.063 jogos) / **70,3%** de aproveitamento de pontos.
- Vantagem de jogar em casa: **80,1%** de aproveitamento como mandante vs **58,6%** fora — uma diferença de **21,5 pontos percentuais**.
- Maior artilheiro histórico: **Neymar**, com 79 gols em 128 jogos — superou Pelé (77) em setembro de 2023 e está com a marca congelada desde então por lesões.
- Retrospecto direto Brasil x Argentina: 110 jogos, 43 vitórias do Brasil, 26 empates, 41 vitórias da Argentina.

## Rascunho para post no LinkedIn

> ⚽ Analisei os 1.063 jogos da Seleção Brasileira desde 1914 (dado público, atualizado até a Copa de 2026) e um número chamou atenção: o aproveitamento do Brasil como mandante é 21,5 pontos percentuais maior do que fora de casa (80,1% vs 58,6%).
>
> Construí um dashboard interativo em Dash pra explorar isso e mais: desempenho por competição, retrospecto contra os principais rivais, artilheiros históricos (corrigi manualmente essa parte — o dataset público tinha só 47% de cobertura dos gols) e a campanha de 2026 em tempo real.
>
> 🔗 [link do dashboard] · código no GitHub: [link]
>
> Buscando oportunidades de estágio em dados — bora trocar uma ideia? 🟢🟡

## Próximos passos possíveis

- Adicionar dados de posse de bola/xG (base atual só tem placar).
- Comparar Brasil com outras seleções (Argentina, Alemanha, Itália) num painel de benchmarking.
- Automatizar a atualização dos dados via GitHub Actions, já que a base de jogos é mantida ativamente.

