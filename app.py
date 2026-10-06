"""NEJ POA — Diagnóstico de Maturidade EJ. Execute: python -m streamlit run app.py"""
from __future__ import annotations

import logging

import streamlit as st

st.set_page_config(page_title="NEJ POA — Diagnóstico de Maturidade EJ", page_icon="◈", layout="wide",
                   initial_sidebar_state="expanded")

from components import pages, sidebar  # noqa: E402
from components.progress import tela_carregamento  # noqa: E402
from utils.helpers import carregar_css, iniciar_estado, rolar_para_topo  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("diagnostico_ej")


def main() -> None:
    carregar_css()
    iniciar_estado()
    if not st.session_state.splash_visto:
        tela_carregamento()
        st.session_state.splash_visto = True
    sidebar.renderizar()
    if st.session_state.concluido:
        pages.pagina_resultado()
    else:
        pages.pagina_questionario()
    if st.session_state.pop("rolar", False):
        rolar_para_topo()


try:
    main()
except Exception as exc:  # noqa: BLE001 - nunca expor traceback ao usuário
    log.exception("Erro inesperado: %s", exc)
    st.error("Ocorreu um erro inesperado, mas suas respostas continuam salvas nesta sessão. "
             "Recarregue a página ou use 'Exportar progresso' na barra lateral.")
    if st.button("Tentar novamente"):
        st.rerun()
