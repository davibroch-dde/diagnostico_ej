"""Telas: identificação, perguntas, observações/conclusão e dashboard de resultados."""
from __future__ import annotations

import re
import time
from datetime import date

import streamlit as st

from components import cards, charts
from components.progress import PAGINAS, barra_progresso, pagina_da_pergunta, stepper
from config.metodologia import (
    CENARIOS, INDICADORES, INDICADORES_POR_DIMENSAO, INDICADORES_TRANSVERSAIS, PESO_ELO_MAIS_FRACO,
)
from config.settings import CAMPOS_IDENTIFICACAO, COR, DIMENSOES, ORDEM_DIMENSOES, faixa_de
from data.perguntas import PERGUNTAS, PERGUNTAS_POR_ID
from services import diagnostico, scoring
from services.gemini import api_configurada, generate_ai_diagnosis
from services.pdf_generator import gerar_pdf
from utils.helpers import STRETCH, hash_respostas, render_html
from utils.validators import ANO_MIN, texto_pendencias, validar_conclusao

NUMERO = {q["id"]: n for n, q in enumerate(PERGUNTAS, start=1)}


# ===================================================================== callbacks
def _ir_pagina(pagina: int) -> None:
    st.session_state.pagina = max(0, min(len(PAGINAS) - 1, pagina))
    st.session_state.concluido = False
    st.session_state.rolar = True


def _mudar(delta: int) -> None:
    _ir_pagina(st.session_state.pagina + delta)


def _salvar_progresso() -> None:
    st.toast("Progresso salvo na sessão. Use 'Exportar progresso' na barra lateral para guardar em arquivo.")


def _salvar_ident(chave: str, wkey: str) -> None:
    valor = st.session_state.get(wkey)
    st.session_state.ident[chave] = valor.strip() if isinstance(valor, str) else valor


def _salvar_obs() -> None:
    st.session_state.observacoes = st.session_state.get("obs_texto", "")


def _salvar_single(qid: str, wkey: str) -> None:
    valor = st.session_state.get(wkey)
    if valor is None:
        st.session_state.respostas.pop(qid, None)
    else:
        st.session_state.respostas[qid] = valor


def _salvar_multi(qid: str, oid: str) -> None:
    q = PERGUNTAS_POR_ID[qid]
    chave = lambda o: f"cb_{qid}_{o['id']}"  # noqa: E731
    alterada = next(o for o in q["opcoes"] if o["id"] == oid)
    if st.session_state.get(chave(alterada)):
        for o in q["opcoes"]:  # exclusividade: "Nenhuma" anula as demais e vice-versa
            if o["id"] != oid and (alterada["excl"] or o["excl"]):
                st.session_state[chave(o)] = False
    marcadas = [o["id"] for o in q["opcoes"] if st.session_state.get(chave(o))]
    if marcadas:
        st.session_state.respostas[qid] = marcadas
    else:
        st.session_state.respostas.pop(qid, None)


# ================================================================= identificação
def _campo_texto(chave: str, rotulo: str, placeholder: str = "") -> None:
    wkey = f"id_{chave}"
    if wkey not in st.session_state:
        st.session_state[wkey] = st.session_state.ident.get(chave, "") or ""
    st.text_input(rotulo, key=wkey, placeholder=placeholder, on_change=_salvar_ident, args=(chave, wkey))


def _campo_numero(chave: str, rotulo: str, minimo: int, maximo: int) -> None:
    wkey = f"id_{chave}"
    if wkey not in st.session_state:
        v = st.session_state.ident.get(chave)
        st.session_state[wkey] = int(v) if isinstance(v, (int, float)) else None
    st.number_input(rotulo, min_value=minimo, max_value=maximo, step=1, value=None, key=wkey,
                    on_change=_salvar_ident, args=(chave, wkey))


def pagina_identificacao() -> None:
    cards.cabecalho_pagina("ETAPA 00 · IDENTIFICAÇÃO", "Conheça a sua Empresa Júnior",
                           "Estas informações personalizam o relatório. Todos os campos, exceto a descrição livre, são obrigatórios.")
    with st.container(border=True, key="qc_ident"):
        c1, c2 = st.columns(2)
        with c1:
            _campo_texto("nome_ej", "Nome da Empresa Júnior")
            _campo_texto("universidade", "Universidade")
            _campo_numero("n_membros", "Número atual de membros", 1, 500)
            _campo_texto("responsavel", "Presidente / responsável pelo preenchimento")
            _campo_texto("gestao", "Período / gestão atual", "Ex.: 2026.1")
        with c2:
            _campo_texto("curso", "Curso / área principal")
            _campo_texto("cidade", "Cidade")
            _campo_numero("ano_fundacao", "Ano de fundação", ANO_MIN, date.today().year)
            _campo_texto("cargo", "Cargo do responsável")
        wkey = "id_situacao"
        if wkey not in st.session_state:
            st.session_state[wkey] = st.session_state.ident.get("situacao", "") or ""
        st.text_area("Como você descreveria atualmente a principal situação da sua EJ?", key=wkey, height=130,
                     placeholder="Momento atual, principais desafios, conquistas recentes, expectativas para a gestão...",
                     on_change=_salvar_ident, args=("situacao", wkey))


# ===================================================================== perguntas
def _render_single(q: dict) -> None:
    wkey = f"w_{q['id']}"
    if wkey not in st.session_state:
        st.session_state[wkey] = st.session_state.respostas.get(q["id"])
    textos = {o["id"]: o["texto"] for o in q["opcoes"]}
    st.radio(q["texto"], list(textos), key=wkey, index=None, format_func=textos.get,
             label_visibility="collapsed", on_change=_salvar_single, args=(q["id"], wkey))


def _render_multi(q: dict) -> None:
    atuais = st.session_state.respostas.get(q["id"], [])
    for o in q["opcoes"]:
        ck = f"cb_{q['id']}_{o['id']}"
        if ck not in st.session_state:
            st.session_state[ck] = o["id"] in atuais
        st.checkbox(o["texto"], key=ck, on_change=_salvar_multi, args=(q["id"], o["id"]))


def pagina_perguntas(pagina: dict) -> None:
    dim = DIMENSOES[pagina["dim"]]
    cards.cabecalho_pagina(f"ETAPA {dim['etapa']} · BLOCO {pagina['parte']}", dim["nome"], dim["descricao"], dim["cor"])
    pendentes = 0
    for qid in pagina["qids"]:
        q = PERGUNTAS_POR_ID[qid]
        respondida = scoring.esta_respondida(q, st.session_state.respostas.get(qid))
        pendentes += 0 if respondida else 1
        with st.container(border=True, key=f"qc_{qid}"):
            cards.cabecalho_pergunta(q, NUMERO[qid], len(PERGUNTAS), respondida)
            (_render_multi if q["tipo"] == "multi" else _render_single)(q)
    if pendentes:
        cards.aviso(f"Esta etapa possui {pendentes} pergunta{'s' if pendentes != 1 else ''} sem resposta. "
                    "Você pode avançar, mas só poderá concluir o diagnóstico com todas respondidas.", "info")


# ======================================================== observações e conclusão
def _ir_para_pergunta(qid: str) -> None:
    _ir_pagina(pagina_da_pergunta(qid))


def _ir_para_identificacao() -> None:
    _ir_pagina(0)


def pagina_observacoes() -> None:
    cards.cabecalho_pagina("ETAPA FINAL", "Observações da EJ",
                           "Use este espaço para contextualizar respostas, relatar problemas específicos, oportunidades, "
                           "dificuldades ou qualquer informação que você considere importante para interpretar o diagnóstico.")
    with st.container(border=True, key="qc_obs"):
        if "obs_texto" not in st.session_state:
            st.session_state.obs_texto = st.session_state.observacoes
        st.text_area("Observações da EJ", key="obs_texto", height=260, label_visibility="collapsed",
                     placeholder="Ex.: mudanças recentes na diretoria, projetos grandes em andamento, contexto do mercado local, "
                                 "ferramentas que estão sendo implantadas, dificuldades específicas...",
                     on_change=_salvar_obs)
        st.caption("Este texto será enviado ao consultor de IA como contexto qualitativo para interpretar as pontuações.")
    _painel_conclusao()


def _painel_conclusao() -> None:
    v = validar_conclusao(st.session_state.ident, st.session_state.respostas)
    if v["ok"]:
        cards.aviso("Tudo certo: todas as perguntas e campos obrigatórios foram preenchidos. Você já pode concluir o diagnóstico.", "ok")
    else:
        cards.aviso(texto_pendencias(v), "warn")
        if v["identificacao"]:
            st.button("Completar identificação: " + ", ".join(v["identificacao"][:3]) + ("..." if len(v["identificacao"]) > 3 else ""),
                      key="jump_ident", on_click=_ir_para_identificacao)
        for qid, texto in v["textos_perguntas"]:
            curto = texto if len(texto) <= 90 else texto[:87] + "..."
            st.button(f"Pergunta {NUMERO[qid]:02d} · {curto}", key=f"jump_{qid}", on_click=_ir_para_pergunta, args=(qid,))

    c1, c2, c3 = st.columns([1, 1, 1.4])
    c1.button("← Voltar", key="obs_voltar", on_click=_mudar, args=(-1,), **STRETCH)
    c2.button("Salvar progresso", key="obs_salvar", on_click=_salvar_progresso, **STRETCH)
    if c3.button("CONCLUIR DIAGNÓSTICO", key="obs_concluir", type="primary", **STRETCH):
        if v["ok"]:
            with st.spinner("Calculando maturidade, cruzando indicadores e priorizando ações..."):
                time.sleep(0.9)
            st.session_state.concluido = True
            st.session_state.rolar = True
            st.rerun()
        else:
            st.error(texto_pendencias(v) + " Complete os itens acima para concluir.")


def barra_navegacao(indice: int) -> None:
    c1, c2, c3 = st.columns([1, 1, 1.4])
    c1.button("← Voltar", key=f"nav_voltar_{indice}", on_click=_mudar, args=(-1,), disabled=indice == 0, **STRETCH)
    c2.button("Salvar progresso", key=f"nav_salvar_{indice}", on_click=_salvar_progresso, **STRETCH)
    c3.button("Continuar →", key=f"nav_continuar_{indice}", type="primary", on_click=_mudar, args=(1,), **STRETCH)


def pagina_questionario() -> None:
    indice = st.session_state.pagina
    pagina = PAGINAS[indice]
    stepper(indice, st.session_state.respostas)
    if pagina["tipo"] == "ident":
        pagina_identificacao()
        barra_navegacao(indice)
    elif pagina["tipo"] == "perguntas":
        pagina_perguntas(pagina)
        barra_navegacao(indice)
    else:
        pagina_observacoes()


# ======================================================================= resultados
def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (texto or "ej").lower()).strip("_") or "ej"


def _aba_visao_geral(ident: dict, scores: dict, diag: dict) -> None:
    cards.hero_resultado(ident, scores)
    cards.grade_dimensoes(scores, faixa_de)
    st.markdown("##### Maturidade por dimensão")
    c1, c2 = st.columns([1, 1])
    c1.plotly_chart(charts.radar(scores), **STRETCH, key="g_radar")
    c2.plotly_chart(charts.matriz_maturidade(scores), **STRETCH, key="g_matriz")
    cards.grade_insights(diag["principais"])
    if scores["ajuste"] > 0:
        cards.aviso(
            f"Índice bruto: {scores['geral_bruto']:.0f}. Foi aplicado um ajuste de -{scores['ajuste']:.1f} ponto(s) pelo elo mais fraco: "
            f"quando uma dimensão fica abaixo de {PESO_ELO_MAIS_FRACO['limite']:.0f}, ela limita o desempenho do conjunto.", "info")
    a, b = st.columns(2)
    with a:
        cards.lista_itens("Principais forças", diag["forcas"], COR["verde"])
        cards.lista_itens("Riscos estratégicos", diag["riscos"], COR["vermelho"])
    with b:
        cards.lista_itens("Principais fragilidades", diag["fragilidades"], "#F97316")
        cards.lista_itens("Oportunidades", diag["oportunidades"], COR["ciano"])


def _aba_indicadores(scores: dict) -> None:
    st.markdown("Cada dimensão é composta por subdimensões e indicadores. "
                "Todos usam a mesma escala (0 a 100; quanto maior, melhor).")
    for dim in ORDEM_DIMENSOES:
        cfg = DIMENSOES[dim]
        rotulo, cor, _ = faixa_de(scores["dim"][dim])
        with st.expander(f"{cfg['glifo']}  {cfg['nome']}  ·  {scores['dim'][dim]:.0f}  ·  {rotulo}", expanded=dim == "processos"):
            a, b = st.columns(2)
            a.markdown("**Subdimensões**")
            a.plotly_chart(charts.barras_subdimensoes(scores, dim), **STRETCH, key=f"g_sub_{dim}")
            b.markdown("**Indicadores derivados**")
            b.plotly_chart(charts.barras_indicadores(scores, INDICADORES_POR_DIMENSAO[dim]), **STRETCH, key=f"g_ind_{dim}")
            for ind in INDICADORES_POR_DIMENSAO[dim]:
                st.caption(f"**{INDICADORES[ind]['nome']}** — {INDICADORES[ind]['desc']}")
    with st.expander("◇  Indicadores transversais (cruzam várias dimensões)", expanded=True):
        st.plotly_chart(charts.barras_transversais(scores), **STRETCH, key="g_transv")
        for ind in INDICADORES_TRANSVERSAIS:
            st.caption(f"**{INDICADORES[ind]['nome']}** — {INDICADORES[ind]['desc']}")


def _aba_gargalos(diag: dict) -> None:
    st.markdown("O sistema cruza indicadores de dimensões diferentes para mostrar **onde a EJ está perdendo capacidade**.")
    if not diag["gargalos"]:
        cards.aviso("Nenhum cruzamento crítico foi identificado: não há descompassos relevantes entre as dimensões avaliadas.", "ok")
        return
    for g in diag["gargalos"]:
        cards.card_gargalo(g)


def _aba_prioridades(diag: dict) -> None:
    acoes = diag["acoes"]
    if not acoes:
        cards.aviso("Todos os indicadores estão em nível elevado. Não há ações prioritárias; mantenha e documente as boas práticas.", "ok")
        return
    st.markdown("##### Matriz Impacto × Urgência")
    a, b = st.columns([1.15, 1])
    a.plotly_chart(charts.matriz_prioridade(acoes), **STRETCH, key="g_prio")
    with b:
        cards.tabela_prioridades(acoes)
    st.markdown("##### Plano de ação 30 / 60 / 90 dias")
    abas = st.tabs(["Próximos 30 dias", "60 dias", "90 dias"])
    for aba, h in zip(abas, (30, 60, 90)):
        with aba:
            itens = diag["plano"][h]
            if not itens:
                st.caption("Nenhuma ação priorizada neste horizonte.")
            for n, a_ in enumerate(itens, start=1):
                cards.card_acao(a_, acoes.index(a_) + 1 if a_ in acoes else n)


def _aba_simulacao(scores: dict) -> None:
    st.markdown("Estime se a estrutura atual sustentaria um novo cenário. "
                "É uma **simulação conceitual** baseada nos indicadores deste diagnóstico.")
    cen = st.radio("Cenário", list(CENARIOS), format_func=lambda k: CENARIOS[k]["titulo"], horizontal=True, key="sim_cenario")
    cfg = CENARIOS[cen]
    lo, hi, padrao = cfg["faixa"]
    pct = st.slider(cfg["rotulo_slider"], lo, hi, padrao, step=5, key=f"sim_pct_{cen}")
    sim = diagnostico.simular(scores, cen, pct)
    cards.resultado_simulacao(sim)
    st.plotly_chart(charts.barras_simulacao(sim), **STRETCH, key=f"g_sim_{cen}")
    if sim["gargalos"]:
        st.markdown("**Pontos que se tornariam gargalo:** " + ", ".join(r["nome"] for r in sim["gargalos"]) + ".")
    if sim["atencao"]:
        st.markdown("**Pontos em atenção (margem curta):** " + ", ".join(r["nome"] for r in sim["atencao"]) + ".")
    st.caption(sim["nota_metodologica"])


def _gerar_ia(ident: dict, scores: dict, diag: dict, forcar: bool = False) -> dict:
    h = hash_respostas()
    atual = st.session_state.ia
    if atual and atual["hash"] == h and (atual["resultado"]["ok"] and not forcar):
        return atual["resultado"]
    resultado = generate_ai_diagnosis(ident, st.session_state.observacoes, st.session_state.respostas, scores, diag)
    st.session_state.ia = {"hash": h, "resultado": resultado}
    return resultado


def _gerar_pdf_fluxo(ident: dict, scores: dict, diag: dict) -> None:
    with st.status("Gerando diagnóstico completo...", expanded=True) as status:
        st.write("Consultando o consultor de IA (Gemini)...")
        ia = _gerar_ia(ident, scores, diag)
        if not ia["ok"]:
            st.write("Parecer de IA indisponível; o relatório quantitativo será gerado mesmo assim.")
        st.write("Montando o relatório em PDF...")
        try:
            pdf = gerar_pdf(ident, st.session_state.observacoes, st.session_state.respostas, scores, diag,
                            ia["texto"] if ia["ok"] else None)
            st.session_state.pdf = {"hash": hash_respostas(), "bytes": pdf, "ia_ok": ia["ok"], "erro_ia": ia["erro"]}
            status.update(label="Relatório pronto", state="complete", expanded=False)
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger("diagnostico_ej").exception("Falha ao gerar PDF: %s", exc)
            st.session_state.pdf = None
            status.update(label="Não foi possível gerar o PDF", state="error")
            st.error("Ocorreu um erro ao montar o PDF. Suas respostas foram preservadas; tente novamente.")


def _aba_ia_pdf(ident: dict, scores: dict, diag: dict) -> None:
    st.markdown("O **parecer de IA** interpreta o diagnóstico como um consultor estratégico especializado em EJs. "
                "O **relatório PDF** reúne notas, gráficos, gargalos, plano 30/60/90 e, quando disponível, o parecer.")
    if not api_configurada():
        cards.aviso("A chave GEMINI_API_KEY não está configurada. O relatório quantitativo continua disponível; "
                    "configure a chave (veja o README) para incluir o parecer de IA.", "warn")
    c1, c2 = st.columns(2)
    if c1.button("Gerar parecer com IA", key="btn_ia", **STRETCH):
        with st.spinner("O consultor de IA está analisando o diagnóstico. Isso pode levar até um minuto..."):
            _gerar_ia(ident, scores, diag, forcar=True)
    gerar_pdf_clicado = c2.button("GERAR RELATÓRIO PDF", key="btn_pdf", type="primary", **STRETCH)
    if gerar_pdf_clicado:
        _gerar_pdf_fluxo(ident, scores, diag)

    pdf = st.session_state.pdf
    if pdf and pdf["hash"] == hash_respostas():
        if pdf["ia_ok"]:
            cards.aviso("Relatório completo gerado, com parecer de IA incluído.", "ok")
        else:
            cards.aviso("Relatório quantitativo gerado. O parecer de IA não foi incluído: " + (pdf["erro_ia"] or "indisponível") +
                        " Suas respostas foram preservadas e você pode tentar novamente.", "warn")
        st.download_button("BAIXAR RELATÓRIO PDF", data=pdf["bytes"], type="primary", mime="application/pdf",
                           file_name=f"diagnostico_{_slug(ident.get('nome_ej'))}_{date.today():%Y%m%d}.pdf",
                           key="dl_pdf", **STRETCH)

    ia = st.session_state.ia
    if ia and ia["hash"] == hash_respostas():
        if ia["resultado"]["ok"]:
            st.markdown("---")
            st.caption(f"Parecer gerado por IA ({ia['resultado']['modelo']}). Revise o conteúdo antes de compartilhar.")
            st.markdown(ia["resultado"]["texto"])
        else:
            cards.aviso("Parecer de IA não gerado: " + (ia["resultado"]["erro"] or "indisponível"), "warn")


def pagina_resultado() -> None:
    ident = st.session_state.ident
    scores = scoring.calcular(st.session_state.respostas)
    diag = diagnostico.analisar(ident, scores)
    st.button("← Revisar respostas", key="res_voltar", on_click=_ir_pagina, args=(len(PAGINAS) - 1,))
    abas = st.tabs(["Visão geral", "Indicadores", "Gargalos", "Prioridades e plano", "E se?", "Parecer de IA e PDF"])
    with abas[0]:
        _aba_visao_geral(ident, scores, diag)
    with abas[1]:
        _aba_indicadores(scores)
    with abas[2]:
        _aba_gargalos(diag)
    with abas[3]:
        _aba_prioridades(diag)
    with abas[4]:
        _aba_simulacao(scores)
    with abas[5]:
        _aba_ia_pdf(ident, scores, diag)
