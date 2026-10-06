"""Barra lateral: marca, progresso, atalhos, salvar/restaurar e status da IA."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.progress import PAGINAS, barra_progresso, primeira_pagina_da_dimensao, progresso_por_dimensao
from config.settings import APP_SHORT, APP_VERSION, DIMENSOES, ORDEM_DIMENSOES
from services.gemini import api_configurada
from utils.helpers import STRETCH, esc, exportar_progresso, importar_progresso, render_html, reiniciar


def _ir(pagina: int) -> None:
    st.session_state.pagina = pagina
    st.session_state.concluido = False
    st.session_state.rolar = True


def _pedir_reinicio() -> None:
    st.session_state.confirmar_reinicio = True


def _cancelar_reinicio() -> None:
    st.session_state.confirmar_reinicio = False


def _confirmar_reinicio() -> None:
    reiniciar()


def renderizar() -> None:
    with st.sidebar:
        render_html(f"""
        <div class="brand">
          <div class="brand-mark">N</div>
          <div><div class="brand-name">{esc(APP_SHORT)}</div><div class="brand-sub">Diagnóstico de Maturidade EJ</div></div>
        </div>""")

        barra_progresso(st.session_state.respostas, "Progresso")

        st.markdown('<div class="side-title">ETAPAS</div>', unsafe_allow_html=True)
        st.button("Identificação", key="side_ident", on_click=_ir, args=(0,), **STRETCH)
        prog = progresso_por_dimensao(st.session_state.respostas)
        for dim in ORDEM_DIMENSOES:
            feitas, total = prog[dim]
            st.button(
                f"{DIMENSOES[dim]['glifo']}  {DIMENSOES[dim]['curto']}  ·  {feitas}/{total}",
                key=f"side_{dim}", on_click=_ir, args=(primeira_pagina_da_dimensao(dim),), **STRETCH,
            )
        st.button("Observações e conclusão", key="side_obs", on_click=_ir, args=(len(PAGINAS) - 1,), **STRETCH)

        st.markdown('<div class="side-title">PROGRESSO</div>', unsafe_allow_html=True)
        nome_arquivo = f"progresso_diagnostico_{datetime.now():%Y%m%d_%H%M}.json"
        st.download_button(
            "Exportar progresso (.json)", data=exportar_progresso(), file_name=nome_arquivo,
            mime="application/json", key="side_export", **STRETCH,
        )
        enviado = st.file_uploader("Restaurar progresso", type=["json"], key="side_upload", label_visibility="collapsed")
        if enviado is not None:
            marca = f"{enviado.name}-{enviado.size}"
            if marca != st.session_state.import_id:
                ok, msg = importar_progresso(enviado.getvalue())
                st.session_state.import_id = marca
                st.session_state.msg_import = (ok, msg)
                st.rerun()
        if st.session_state.get("msg_import"):
            ok, msg = st.session_state.msg_import
            (st.success if ok else st.error)(msg)

        st.markdown('<div class="side-title">INTELIGÊNCIA ARTIFICIAL</div>', unsafe_allow_html=True)
        if api_configurada():
            render_html('<div class="status ok"><i></i>Gemini configurado</div>')
        else:
            render_html('<div class="status off"><i></i>Gemini não configurado</div>')
            st.caption("O diagnóstico quantitativo funciona sem IA. Configure a chave no README para gerar o parecer.")
            with st.expander("Usar chave nesta sessão"):
                st.text_input("GEMINI_API_KEY", type="password", key="api_key_sessao",
                              help="Fica apenas na memória desta sessão e não é gravada em disco.")

        st.markdown("<div class='side-gap'></div>", unsafe_allow_html=True)
        if st.session_state.get("confirmar_reinicio"):
            st.warning("Isto apagará todas as respostas desta sessão.")
            c1, c2 = st.columns(2)
            c1.button("Apagar", key="reset_sim", on_click=_confirmar_reinicio, **STRETCH)
            c2.button("Cancelar", key="reset_nao", on_click=_cancelar_reinicio, **STRETCH)
        else:
            st.button("Reiniciar diagnóstico", key="reset_pedir", on_click=_pedir_reinicio, **STRETCH)

        st.markdown(f'<div class="side-foot">{esc(APP_SHORT)} · v{esc(APP_VERSION)}<br>Dados mantidos apenas nesta sessão.</div>',
                    unsafe_allow_html=True)
