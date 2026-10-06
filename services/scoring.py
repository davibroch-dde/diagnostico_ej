"""Cálculo de pontuações: pergunta -> indicador -> dimensão -> Índice Geral.

A metodologia completa está documentada em config/metodologia.py.
"""
from __future__ import annotations

from collections import defaultdict

from config.metodologia import INDICADORES, PESO_ELO_MAIS_FRACO
from config.settings import DIMENSOES, ORDEM_DIMENSOES, faixa_de
from data.perguntas import PERGUNTAS, PERGUNTAS_POR_ID


def esta_respondida(q: dict, resposta) -> bool:
    if q["tipo"] == "multi":
        return bool(resposta)
    return resposta is not None and resposta in {o["id"] for o in q["opcoes"]}


def nota_pergunta(q: dict, resposta) -> float | None:
    """Nota 0–100 da pergunta, ou None se não respondida."""
    if not esta_respondida(q, resposta):
        return None
    pontos = {o["id"]: o["pontos"] for o in q["opcoes"]}
    if q["tipo"] == "multi":
        return float(min(100, sum(pontos.get(r, 0) for r in resposta)))
    return float(pontos[resposta])


def perguntas_pendentes(respostas: dict) -> list[str]:
    return [q["id"] for q in PERGUNTAS if not esta_respondida(q, respostas.get(q["id"]))]


def _media_ponderada(pares: list[tuple[float, float]]) -> float:
    total = sum(p for _, p in pares)
    if total <= 0:
        return 0.0
    return sum(v * p for v, p in pares) / total


def perfil_de_equilibrio(notas_dim: dict[str, float]) -> tuple[str, float]:
    spread = max(notas_dim.values()) - min(notas_dim.values())
    if spread < 15:
        return "Equilibrado", spread
    if spread < 30:
        return "Moderadamente assimétrico", spread
    return "Fortemente assimétrico", spread


def calcular(respostas: dict) -> dict:
    """Calcula todas as notas a partir das respostas (dict id_pergunta -> resposta)."""
    notas_q: dict[str, float] = {}
    for q in PERGUNTAS:
        n = nota_pergunta(q, respostas.get(q["id"]))
        if n is not None:
            notas_q[q["id"]] = n

    # Dimensões e subdimensões
    por_dim: dict[str, list] = defaultdict(list)
    por_sub: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for qid, n in notas_q.items():
        q = PERGUNTAS_POR_ID[qid]
        por_dim[q["dim"]].append((n, q["peso"]))
        por_sub[q["dim"]][q["sub"]].append((n, q["peso"]))
    notas_dim = {d: round(_media_ponderada(por_dim.get(d, [])), 1) for d in ORDEM_DIMENSOES}
    notas_sub = {
        d: {s: round(_media_ponderada(v), 1) for s, v in por_sub.get(d, {}).items()}
        for d in ORDEM_DIMENSOES
    }

    # Indicadores
    acum: dict[str, list] = defaultdict(list)
    for qid, n in notas_q.items():
        q = PERGUNTAS_POR_ID[qid]
        for ind, contrib in q["indicadores"].items():
            acum[ind].append((n, q["peso"] * contrib))
    notas_ind = {ind: round(_media_ponderada(acum.get(ind, [])), 1) for ind in INDICADORES}

    # Índice geral com ajuste do elo mais fraco
    bruto = sum(notas_dim[d] * DIMENSOES[d]["peso"] for d in ORDEM_DIMENSOES)
    cfg = PESO_ELO_MAIS_FRACO
    menor = min(notas_dim.values())
    ajuste = 0.0
    if menor < cfg["limite"]:
        ajuste = min(cfg["maximo"], (cfg["limite"] - menor) * cfg["fator"])
    geral = max(0.0, min(100.0, bruto - ajuste))
    rotulo, cor, leitura = faixa_de(geral)
    perfil, spread = perfil_de_equilibrio(notas_dim)

    return {
        "q": notas_q,
        "dim": notas_dim,
        "sub": notas_sub,
        "ind": notas_ind,
        "geral_bruto": round(bruto, 1),
        "ajuste": round(ajuste, 1),
        "geral": round(geral, 1),
        "faixa": rotulo,
        "cor": cor,
        "leitura": leitura,
        "perfil": perfil,
        "spread": round(spread, 1),
        "completude": round(100 * len(notas_q) / len(PERGUNTAS)),
    }
