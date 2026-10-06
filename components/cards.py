"""Cards e blocos HTML da interface (todos os textos são escapados)."""
from __future__ import annotations

from config.settings import COR, DIMENSOES
from utils.helpers import esc, render_html

ROTULOS_INSIGHT = {
    "forca": ("PRINCIPAL FORÇA", COR["verde"]),
    "gargalo": ("PRINCIPAL GARGALO", "#F97316"),
    "oportunidade": ("PRINCIPAL OPORTUNIDADE", COR["ciano"]),
    "risco": ("MAIOR RISCO", COR["vermelho"]),
}


def cabecalho_pagina(etapa: str, titulo: str, descricao: str, cor: str = COR["azul"]) -> None:
    render_html(f"""
    <div class="page-head" style="--accent:{cor}">
      <div class="page-eyebrow">{esc(etapa)}</div>
      <h2>{esc(titulo)}</h2>
      <p>{esc(descricao)}</p>
    </div>""")


def cabecalho_pergunta(q: dict, numero: int, total: int, respondida: bool) -> None:
    cor = DIMENSOES[q["dim"]]["cor"]
    tag_sis = '<span class="tag tag-sis">Visão sistêmica</span>' if q["sistemica"] else ""
    tag_multi = '<span class="tag">Marque todas que se aplicam</span>' if q["tipo"] == "multi" else ""
    dica = q["dica"] or f"Indicador avaliado: {q['avaliado']}."
    estado = "answered" if respondida else "pending"
    check = '<span class="check">✓</span>' if respondida else ""
    render_html(f"""
    <div class="q-state {estado}"></div>
    <div class="q-head" style="--accent:{cor}">
      <div class="q-meta">
        <span class="q-num">{numero:02d}<small>/{total}</small></span>
        <span class="tag tag-sub">{esc(q['sub'])}</span>{tag_sis}{tag_multi}
        <span class="tip" data-tip="{esc(dica)}">?</span>
        {check}
      </div>
      <div class="q-text">{esc(q['texto'])}</div>
      <div class="q-ctx">{esc(q['contexto'])}</div>
    </div>""")


def hero_resultado(ident: dict, scores: dict) -> None:
    cor = scores["cor"]
    render_html(f"""
    <div class="hero" style="--accent:{cor}">
      <div class="hero-eyebrow">DIAGNÓSTICO CONCLUÍDO</div>
      <div class="hero-name">{esc(ident.get('nome_ej', ''))}</div>
      <div class="hero-grid">
        <div>
          <div class="hero-label">ÍNDICE GERAL DE MATURIDADE</div>
          <div class="hero-score">{scores['geral']:.0f}<small>/100</small></div>
        </div>
        <div>
          <div class="hero-label">MATURIDADE</div>
          <div class="hero-badge">{esc(scores['faixa'])}</div>
          <div class="hero-sub">Perfil {esc(scores['perfil'].lower())}</div>
        </div>
      </div>
      <p class="hero-read">{esc(scores['leitura'])}</p>
    </div>""")


def card_dimensao(dim: str, nota: float, faixa: str, cor_faixa: str) -> str:
    cfg = DIMENSOES[dim]
    return f"""
    <div class="dim-card" style="--accent:{cfg['cor']}">
      <div class="dim-top"><span class="glyph">{cfg['glifo']}</span><span>{esc(cfg['curto'])}</span></div>
      <div class="dim-score">{nota:.0f}</div>
      <div class="dim-bar"><div class="dim-fill" style="width:{nota:.0f}%"></div></div>
      <div class="dim-tag" style="color:{cor_faixa}">{esc(faixa)}</div>
    </div>"""


def grade_dimensoes(scores: dict, faixa_fn) -> None:
    cards = "".join(card_dimensao(d, scores["dim"][d], *faixa_fn(scores["dim"][d])[:2]) for d in DIMENSOES)
    render_html(f'<div class="dim-grid">{cards}</div>')


def card_insight(tipo: str, titulo: str, texto: str) -> str:
    rotulo, cor = ROTULOS_INSIGHT[tipo]
    return f"""
    <div class="insight" style="--accent:{cor}">
      <div class="insight-label">{rotulo}</div>
      <div class="insight-title">{esc(titulo)}</div>
      <div class="insight-text">{esc(texto)}</div>
    </div>"""


def grade_insights(principais: dict) -> None:
    html = "".join(card_insight(t, principais[t]["titulo"], principais[t]["texto"]) for t in ROTULOS_INSIGHT)
    render_html(f'<div class="insight-grid">{html}</div>')


def lista_itens(titulo: str, itens: list[dict], cor: str) -> None:
    linhas = "".join(
        f"""<li><div class="li-title">{esc(i['titulo'])}{f'<span class="li-score">{i["nota"]:.0f}</span>' if i.get('nota') is not None else ''}</div>
        <div class="li-text">{esc(i['texto'])}</div></li>"""
        for i in itens
    )
    render_html(f'<div class="list-card" style="--accent:{cor}"><h4>{esc(titulo)}</h4><ul>{linhas}</ul></div>')


def card_gargalo(g: dict) -> None:
    cor = COR["vermelho"] if g["severidade"] == "alta" else COR["amarelo"]
    render_html(f"""
    <div class="gargalo" style="--accent:{cor}">
      <div class="gargalo-head"><span class="sev" style="color:{cor}">SEVERIDADE {esc(g['severidade'].upper())}</span></div>
      <h4>{esc(g['titulo'])}</h4>
      <p>{esc(g['leitura'])}</p>
      <div class="gargalo-cons"><b>Consequência provável:</b> {esc(g['consequencia'])}</div>
    </div>""")


def card_acao(a: dict, numero: int) -> None:
    render_html(f"""
    <div class="acao" style="--accent:{a['cor']}">
      <div class="acao-head">
        <span class="acao-num">{numero:02d}</span>
        <span class="acao-title">{esc(a['nome_indicador'])}</span>
        <span class="pill" style="--pill:{a['cor']}">{esc(a['prioridade'])}</span>
      </div>
      <div class="acao-grid">
        <div><b>Problema</b>{esc(a['problema'])}</div>
        <div><b>Causa provável</b>{esc(a['causa'])}</div>
      </div>
      <div class="acao-do"><b>Ação</b>{esc(a['acao'])}</div>
      <div class="acao-grid">
        <div><b>Resultado esperado</b>{esc(a['resultado'])}</div>
        <div><b>Indicador de sucesso</b>{esc(a['indicador_sucesso'])}</div>
      </div>
      <div class="acao-foot">
        <span>Responsável sugerido: {esc(a['responsavel'])}</span>
        <span>Dificuldade: {esc(a['dificuldade'])}</span>
        <span>Impacto {a['impacto']} · Urgência {a['urgencia']}</span>
      </div>
    </div>""")


def tabela_prioridades(acoes: list[dict]) -> None:
    linhas = "".join(
        f"""<tr><td>{n}</td><td class="t-name">{esc(a['nome_indicador'])}</td>
        <td>{a['impacto']}</td><td>{a['urgencia']}</td>
        <td><span class="pill" style="--pill:{a['cor']}">{esc(a['prioridade'])}</span></td></tr>"""
        for n, a in enumerate(acoes, start=1)
    )
    render_html(f"""
    <table class="prio-table"><thead><tr><th>#</th><th>Ação</th><th>Impacto</th><th>Urgência</th><th>Prioridade</th></tr></thead>
    <tbody>{linhas}</tbody></table>""")


def resultado_simulacao(sim: dict) -> None:
    cor = {"ok": COR["verde"], "atencao": COR["amarelo"], "critico": COR["vermelho"]}[sim["nivel"]]
    render_html(f"""
    <div class="sim-verdict" style="--accent:{cor}">
      <div class="insight-label">LEITURA DA SIMULAÇÃO</div>
      <div class="sim-q">{esc(sim['pergunta'])}</div>
      <div class="sim-v">{esc(sim['veredito'])}</div>
    </div>""")


def aviso(texto: str, tipo: str = "info") -> None:
    render_html(f'<div class="notice notice-{tipo}">{esc(texto)}</div>')
