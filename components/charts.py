"""Gráficos Plotly no tema escuro da plataforma."""
from __future__ import annotations

import plotly.graph_objects as go

from config.metodologia import INDICADORES, INDICADORES_POR_DIMENSAO, INDICADORES_TRANSVERSAIS
from config.settings import COR, DIMENSOES, ORDEM_DIMENSOES

FONTE = "Inter, 'Segoe UI', system-ui, sans-serif"


def _rgba(hex_cor: str, alpha: float) -> str:
    h = hex_cor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _base(fig: go.Figure, altura: int, margem=(10, 10, 10, 10)) -> go.Figure:
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONTE, color="#C9D1E3", size=13),
        margin=dict(l=margem[0], r=margem[1], t=margem[2], b=margem[3]),
        hoverlabel=dict(bgcolor="#111833", bordercolor="#3B82F6", font=dict(family=FONTE, color="#E6EAF5")),
    )
    return fig


def cor_da_nota(nota: float) -> str:
    if nota <= 20:
        return COR["vermelho"]
    if nota <= 40:
        return "#F97316"
    if nota <= 60:
        return COR["amarelo"]
    if nota <= 80:
        return COR["azul"]
    return COR["verde"]


def radar(scores: dict) -> go.Figure:
    nomes = [DIMENSOES[d]["curto"] for d in ORDEM_DIMENSOES]
    valores = [scores["dim"][d] for d in ORDEM_DIMENSOES]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores + valores[:1], theta=nomes + nomes[:1], fill="toself", name="Maturidade atual",
        line=dict(color=COR["ciano"], width=3), fillcolor=_rgba(COR["azul"], 0.28),
        marker=dict(size=8, color=COR["ciano"]),
        hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[80] * 5, theta=nomes + nomes[:1], name="Meta: Estruturado (80)",
        line=dict(color=_rgba(COR["verde"], 0.55), width=1.5, dash="dot"), hoverinfo="skip",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], tickvals=[20, 40, 60, 80, 100], gridcolor="#1E2747",
                            linecolor="#1E2747", tickfont=dict(size=10, color="#6B7799")),
            angularaxis=dict(gridcolor="#1E2747", linecolor="#1E2747", tickfont=dict(size=13, color="#E6EAF5")),
        ),
        showlegend=True, legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center", font=dict(size=11)),
    )
    return _base(fig, 380, (40, 40, 20, 30))


def gauge(valor: float, cor: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=valor,
        number=dict(font=dict(size=54, color="#FFFFFF", family=FONTE), suffix="<span style='font-size:20px;color:#8E9AB8'>/100</span>"),
        gauge=dict(
            axis=dict(range=[0, 100], tickvals=[0, 20, 40, 60, 80, 100], tickcolor="#3A4468", tickfont=dict(size=10, color="#6B7799")),
            bar=dict(color=cor, thickness=0.28), bgcolor="rgba(0,0,0,0)", borderwidth=0,
            steps=[
                dict(range=[0, 20], color=_rgba(COR["vermelho"], 0.18)),
                dict(range=[20, 40], color=_rgba("#F97316", 0.18)),
                dict(range=[40, 60], color=_rgba(COR["amarelo"], 0.18)),
                dict(range=[60, 80], color=_rgba(COR["azul"], 0.18)),
                dict(range=[80, 100], color=_rgba(COR["verde"], 0.18)),
            ],
        ),
    ))
    return _base(fig, 280, (30, 30, 20, 10))


def matriz_maturidade(scores: dict) -> go.Figure:
    """Barras horizontais das quatro dimensões (a 'Matriz de Maturidade')."""
    ordem = ORDEM_DIMENSOES[::-1]
    fig = go.Figure(go.Bar(
        y=[DIMENSOES[d]["curto"] for d in ordem], x=[scores["dim"][d] for d in ordem], orientation="h",
        marker=dict(color=[DIMENSOES[d]["cor"] for d in ordem], line=dict(width=0)),
        text=[f"{scores['dim'][d]:.0f}" for d in ordem], textposition="outside",
        textfont=dict(color="#FFFFFF", size=15), cliponaxis=False,
        hovertemplate="%{y}: %{x:.0f}<extra></extra>",
    ))
    for limite in (20, 40, 60, 80):
        fig.add_vline(x=limite, line=dict(color="#1E2747", width=1, dash="dot"))
    fig.update_xaxes(range=[0, 108], showgrid=False, zeroline=False, tickvals=[0, 20, 40, 60, 80, 100],
                     tickfont=dict(color="#6B7799", size=10))
    fig.update_yaxes(showgrid=False, tickfont=dict(size=14, color="#E6EAF5"))
    fig.update_layout(bargap=0.38)
    return _base(fig, 300, (10, 30, 10, 10))


def barras_subdimensoes(scores: dict, dim: str) -> go.Figure:
    subs = scores["sub"].get(dim, {})
    itens = sorted(subs.items(), key=lambda kv: kv[1])
    fig = go.Figure(go.Bar(
        y=[k for k, _ in itens], x=[v for _, v in itens], orientation="h",
        marker=dict(color=[cor_da_nota(v) for _, v in itens]),
        text=[f"{v:.0f}" for _, v in itens], textposition="outside", textfont=dict(color="#FFFFFF"), cliponaxis=False,
        hovertemplate="%{y}: %{x:.0f}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 110], showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color="#C9D1E3"))
    fig.update_layout(bargap=0.4)
    return _base(fig, max(150, 52 * len(itens) + 30), (10, 30, 5, 5))


def barras_indicadores(scores: dict, ids: list[str]) -> go.Figure:
    itens = sorted(((INDICADORES[i]["nome"], scores["ind"][i]) for i in ids), key=lambda kv: kv[1])
    fig = go.Figure(go.Bar(
        y=[n for n, _ in itens], x=[v for _, v in itens], orientation="h",
        marker=dict(color=[cor_da_nota(v) for _, v in itens]),
        text=[f"{v:.0f}" for _, v in itens], textposition="outside", textfont=dict(color="#FFFFFF"), cliponaxis=False,
        hovertemplate="%{y}: %{x:.0f}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 110], showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(size=12, color="#C9D1E3"))
    fig.update_layout(bargap=0.38)
    return _base(fig, max(170, 46 * len(itens) + 30), (10, 30, 5, 5))


def barras_transversais(scores: dict) -> go.Figure:
    return barras_indicadores(scores, INDICADORES_TRANSVERSAIS)


def barras_todos_indicadores(scores: dict) -> go.Figure:
    ids = [i for d in ORDEM_DIMENSOES for i in INDICADORES_POR_DIMENSAO[d]]
    return barras_indicadores(scores, ids)


def matriz_prioridade(acoes: list[dict]) -> go.Figure:
    """Dispersão Impacto x Urgência com quadrantes."""
    fig = go.Figure()
    fig.add_shape(type="rect", x0=50, x1=100, y0=50, y1=100, fillcolor=_rgba(COR["vermelho"], 0.07), line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=0, x1=50, y0=50, y1=100, fillcolor=_rgba(COR["azul"], 0.06), line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=50, x1=100, y0=0, y1=50, fillcolor=_rgba(COR["amarelo"], 0.05), line=dict(width=0), layer="below")
    for texto, x, y in (("AGIR AGORA", 96, 97), ("PLANEJAR", 4, 97), ("RESOLVER RÁPIDO", 96, 3), ("MONITORAR", 4, 3)):
        fig.add_annotation(x=x, y=y, text=texto, showarrow=False, font=dict(size=10, color="#4E5A82"),
                           xanchor="right" if x > 50 else "left", yanchor="top" if y > 50 else "bottom")
    if acoes:
        fig.add_trace(go.Scatter(
            x=[a["urgencia"] for a in acoes], y=[a["impacto"] for a in acoes], mode="markers+text",
            text=[str(n) for n in range(1, len(acoes) + 1)], textposition="middle center",
            textfont=dict(color="#05070D", size=11, family=FONTE),
            marker=dict(size=26, color=[a["cor"] for a in acoes], line=dict(color="#FFFFFF", width=1.2), opacity=0.95),
            customdata=[[a["nome_indicador"], a["prioridade"]] for a in acoes],
            hovertemplate="<b>%{customdata[0]}</b><br>Impacto: %{y} | Urgência: %{x}<br>Prioridade: %{customdata[1]}<extra></extra>",
        ))
    fig.update_xaxes(range=[0, 100], title="Urgência", gridcolor="#141B36", zeroline=False, tickfont=dict(color="#6B7799"))
    fig.update_yaxes(range=[0, 100], title="Impacto potencial", gridcolor="#141B36", zeroline=False, tickfont=dict(color="#6B7799"))
    fig.update_layout(showlegend=False)
    return _base(fig, 430, (10, 10, 10, 10))


def barras_simulacao(sim: dict) -> go.Figure:
    linhas = sim["linhas"][::-1]
    cores_status = {"Gargalo": COR["vermelho"], "Atenção": COR["amarelo"], "Suporta": COR["verde"]}
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[l["nome"] for l in linhas], x=[l["nota"] for l in linhas], orientation="h", name="Nota atual",
        marker=dict(color=[cores_status[l["status"]] for l in linhas]),
        text=[f"{l['nota']:.0f}" for l in linhas], textposition="inside", textfont=dict(color="#05070D"),
        hovertemplate="%{y}<br>Nota atual: %{x:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        y=[l["nome"] for l in linhas], x=[l["exigido"] for l in linhas], mode="markers", name="Nível exigido",
        marker=dict(symbol="diamond", size=13, color="#FFFFFF", line=dict(color="#05070D", width=1)),
        hovertemplate="%{y}<br>Nível exigido: %{x:.0f}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 100], gridcolor="#141B36", tickfont=dict(color="#6B7799"))
    fig.update_yaxes(tickfont=dict(size=12, color="#C9D1E3"))
    fig.update_layout(bargap=0.4, legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)))
    return _base(fig, max(260, 48 * len(linhas) + 70), (10, 20, 30, 10))
