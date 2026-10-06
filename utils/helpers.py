"""Funções utilitárias: HTML seguro, CSS, estado da sessão, exportação/importação de progresso."""
from __future__ import annotations

import hashlib
import html as _html
import inspect
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
FORMATO_PROGRESSO = "nej-poa-diagnostico-v1"


def _largura_total() -> dict:
    """Compatível com versões novas (width='stretch') e antigas (use_container_width)."""
    params = inspect.signature(st.button).parameters
    if "width" in params:
        return {"width": "stretch"}
    return {"use_container_width": True}


STRETCH = _largura_total()


def esc(texto) -> str:
    return _html.escape("" if texto is None else str(texto), quote=True)


def render_html(html: str) -> None:
    """Renderiza HTML via markdown sem que linhas indentadas virem bloco de código."""
    limpo = "\n".join(linha.strip() for linha in html.splitlines() if linha.strip())
    st.markdown(limpo, unsafe_allow_html=True)


def carregar_css() -> None:
    css = (RAIZ / "assets" / "style.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def rolar_para_topo() -> None:
    """Leva a rolagem ao topo após trocar de etapa (best effort; ignora falhas)."""
    js = ("for (const s of ['[data-testid=\"stMain\"]','section.main','.main']) {"
          "const el = document.querySelector(s); if (el) { el.scrollTo({top: 0, behavior: 'smooth'}); } }")
    try:
        if "unsafe_allow_javascript" in inspect.signature(st.html).parameters:
            st.html(f"<script>{js}</script>", unsafe_allow_javascript=True)
            return
    except Exception:
        pass
    try:  # versões antigas do Streamlit
        import streamlit.components.v1 as components
        components.html(f"<script>const document = window.parent.document; {js}</script>", height=0)
    except Exception:
        pass


# --------------------------------------------------------------------- estado
def iniciar_estado() -> None:
    st.session_state.setdefault("respostas", {})
    st.session_state.setdefault("ident", {})
    st.session_state.setdefault("observacoes", "")
    st.session_state.setdefault("pagina", 0)
    st.session_state.setdefault("concluido", False)
    st.session_state.setdefault("ia", None)       # {'hash', 'resultado'}
    st.session_state.setdefault("pdf", None)      # {'hash', 'bytes', 'ia_ok'}
    st.session_state.setdefault("splash_visto", False)
    st.session_state.setdefault("import_id", None)


def hash_respostas() -> str:
    """Identifica o conjunto de dados atual (invalida IA/PDF quando algo muda)."""
    base = json.dumps(
        {"r": st.session_state.respostas, "i": st.session_state.ident, "o": st.session_state.observacoes},
        sort_keys=True, ensure_ascii=False, default=str,
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def montar_payload() -> dict:
    """Payload serializável do diagnóstico. Fronteira de dados para uma futura integração com banco."""
    return {
        "formato": FORMATO_PROGRESSO,
        "salvo_em": datetime.now().isoformat(timespec="seconds"),
        "ident": st.session_state.ident,
        "respostas": st.session_state.respostas,
        "observacoes": st.session_state.observacoes,
        "pagina": st.session_state.pagina,
    }


def exportar_progresso() -> str:
    return json.dumps(montar_payload(), ensure_ascii=False, indent=2, default=str)


def importar_progresso(conteudo: bytes) -> tuple[bool, str]:
    """Restaura um progresso salvo. Retorna (sucesso, mensagem)."""
    try:
        dados = json.loads(conteudo.decode("utf-8"))
    except Exception:
        return False, "O arquivo não é um JSON válido."
    if not isinstance(dados, dict) or dados.get("formato") != FORMATO_PROGRESSO:
        return False, "Este arquivo não foi gerado por este sistema."
    from data.perguntas import PERGUNTAS_POR_ID

    respostas = {}
    for qid, valor in (dados.get("respostas") or {}).items():
        q = PERGUNTAS_POR_ID.get(qid)
        if not q:
            continue
        validos = {o["id"] for o in q["opcoes"]}
        if q["tipo"] == "multi" and isinstance(valor, list):
            filtrado = [v for v in valor if v in validos]
            if filtrado:
                respostas[qid] = filtrado
        elif q["tipo"] == "single" and valor in validos:
            respostas[qid] = valor
    st.session_state.respostas = respostas
    st.session_state.ident = {k: v for k, v in (dados.get("ident") or {}).items() if isinstance(k, str)}
    st.session_state.observacoes = str(dados.get("observacoes") or "")
    st.session_state.pagina = int(dados.get("pagina") or 0)
    st.session_state.concluido = False
    st.session_state.ia = None
    st.session_state.pdf = None
    limpar_widgets()
    return True, "Progresso restaurado com sucesso."


def limpar_widgets() -> None:
    """Remove o estado dos widgets para que sejam recriados a partir das respostas salvas."""
    for chave in list(st.session_state.keys()):
        if isinstance(chave, str) and chave.startswith(("w_", "cb_", "id_", "obs_")):
            del st.session_state[chave]


def reiniciar() -> None:
    for chave in list(st.session_state.keys()):
        if chave != "splash_visto":
            del st.session_state[chave]
    iniciar_estado()
    st.session_state.splash_visto = True
