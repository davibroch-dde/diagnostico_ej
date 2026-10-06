"""Etapas do questionário, stepper, barra de progresso e tela de carregamento."""
from __future__ import annotations

import time

import streamlit as st

from config.settings import APP_SHORT, DIMENSOES, ORDEM_DIMENSOES
from data.perguntas import PERGUNTAS_POR_DIM
from services.scoring import esta_respondida
from utils.helpers import esc, render_html

PERGUNTAS_POR_PAGINA = 3


def construir_paginas() -> list[dict]:
    """Lista ordenada de páginas: identificação, blocos de perguntas por dimensão e observações."""
    paginas = [{"tipo": "ident", "titulo": "Identificação", "dim": None, "qids": []}]
    for dim in ORDEM_DIMENSOES:
        qids = [q["id"] for q in PERGUNTAS_POR_DIM[dim]]
        blocos = [qids[i:i + PERGUNTAS_POR_PAGINA] for i in range(0, len(qids), PERGUNTAS_POR_PAGINA)]
        for n, bloco in enumerate(blocos, start=1):
            paginas.append({
                "tipo": "perguntas", "dim": dim, "qids": bloco,
                "titulo": DIMENSOES[dim]["nome"], "parte": f"{n}/{len(blocos)}",
            })
    paginas.append({"tipo": "obs", "titulo": "Observações e conclusão", "dim": None, "qids": []})
    return paginas


PAGINAS = construir_paginas()


def primeira_pagina_da_dimensao(dim: str) -> int:
    return next(i for i, p in enumerate(PAGINAS) if p["dim"] == dim)


def pagina_da_pergunta(qid: str) -> int:
    return next(i for i, p in enumerate(PAGINAS) if qid in p["qids"])


def progresso_por_dimensao(respostas: dict) -> dict[str, tuple[int, int]]:
    saida = {}
    for dim in ORDEM_DIMENSOES:
        qs = PERGUNTAS_POR_DIM[dim]
        saida[dim] = (sum(esta_respondida(q, respostas.get(q["id"])) for q in qs), len(qs))
    return saida


def stepper(pagina_atual: int, respostas: dict) -> None:
    """Navegação visual em 4 estágios (uma por dimensão)."""
    atual = PAGINAS[pagina_atual]
    prog = progresso_por_dimensao(respostas)
    idx_atual = ORDEM_DIMENSOES.index(atual["dim"]) if atual["dim"] else (-1 if atual["tipo"] == "ident" else 99)
    partes = []
    for n, dim in enumerate(ORDEM_DIMENSOES):
        feitas, total = prog[dim]
        if n == idx_atual:
            estado = "active"
        elif feitas == total or n < idx_atual:
            estado = "done"
        else:
            estado = "todo"
        marca = "✓" if (feitas == total and n != idx_atual) else DIMENSOES[dim]["etapa"]
        partes.append(f"""
        <div class="step {estado}" style="--accent:{DIMENSOES[dim]['cor']}">
          <div class="dot">{marca}</div>
          <div class="lbl">{esc(DIMENSOES[dim]['curto'])}<small>{feitas}/{total}</small></div>
        </div>""")
        if n < len(ORDEM_DIMENSOES) - 1:
            cheio = "full" if feitas == total else ""
            partes.append(f'<div class="line {cheio}"></div>')
    render_html(f'<div class="stepper">{"".join(partes)}</div>')


def barra_progresso(respostas: dict, rotulo: str = "Progresso do diagnóstico") -> None:
    total = sum(len(v) for v in PERGUNTAS_POR_DIM.values())
    feitas = sum(f for f, _ in progresso_por_dimensao(respostas).values())
    pct = round(100 * feitas / total)
    render_html(f"""
    <div class="progress-wrap">
      <div class="progress-top"><span>{esc(rotulo)}</span><span>{feitas} de {total} perguntas · {pct}%</span></div>
      <div class="progress"><div class="progress-fill" style="width:{pct}%"></div></div>
    </div>""")


def tela_carregamento(duracao: float = 1.4) -> None:
    """Splash animado exibido uma vez por sessão."""
    caixa = st.empty()
    caixa.markdown(
        f"""<div class="splash"><div class="splash-ring"></div>
        <div class="splash-title">{esc(APP_SHORT)}</div>
        <div class="splash-sub">Diagnóstico de Maturidade EJ</div>
        <div class="splash-bar"><span></span></div></div>""",
        unsafe_allow_html=True,
    )
    time.sleep(duracao)
    caixa.empty()
