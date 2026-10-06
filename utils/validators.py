"""Validações do questionário e da identificação."""
from __future__ import annotations

from datetime import date

from config.settings import CAMPOS_IDENTIFICACAO
from data.perguntas import PERGUNTAS_POR_ID
from services.scoring import perguntas_pendentes

ANO_MIN = 1980


def campos_identificacao_pendentes(ident: dict) -> list[str]:
    """Rótulos dos campos obrigatórios de identificação ainda não preenchidos."""
    pendentes = []
    ano_max = date.today().year
    for chave, rotulo in CAMPOS_IDENTIFICACAO:
        v = ident.get(chave)
        if chave == "n_membros":
            ok = isinstance(v, (int, float)) and 1 <= v <= 500
        elif chave == "ano_fundacao":
            ok = isinstance(v, (int, float)) and ANO_MIN <= v <= ano_max
        else:
            ok = isinstance(v, str) and len(v.strip()) >= 2
        if not ok:
            pendentes.append(rotulo)
    return pendentes


def validar_conclusao(ident: dict, respostas: dict) -> dict:
    """Resumo do que impede a conclusão do diagnóstico."""
    pend_q = perguntas_pendentes(respostas)
    pend_id = campos_identificacao_pendentes(ident)
    return {
        "ok": not pend_q and not pend_id,
        "perguntas": pend_q,
        "identificacao": pend_id,
        "textos_perguntas": [(qid, PERGUNTAS_POR_ID[qid]["texto"]) for qid in pend_q],
    }


def texto_pendencias(v: dict) -> str:
    partes = []
    n = len(v["perguntas"])
    if n:
        partes.append(f"Você possui {n} pergunta{'s' if n != 1 else ''} pendente{'s' if n != 1 else ''}.")
    m = len(v["identificacao"])
    if m:
        partes.append(f"Faltam {m} campo{'s' if m != 1 else ''} de identificação.")
    return " ".join(partes)
