"""Integração com o Google Gemini: o modelo atua como consultor estratégico de EJs.

A chave é lida (nesta ordem) de: chave informada na sessão, st.secrets["GEMINI_API_KEY"],
variável de ambiente GEMINI_API_KEY (ou arquivo .env). Nunca fica no código.
"""
from __future__ import annotations

import logging
import os

from config.settings import (
    DIMENSOES, GEMINI_MAX_OUTPUT_TOKENS, GEMINI_MODELS, GEMINI_TIMEOUT_MS, ORDEM_DIMENSOES,
)
from services.diagnostico import respostas_legiveis
from config.metodologia import INDICADORES

log = logging.getLogger("diagnostico_ej.gemini")

SYSTEM_INSTRUCTION = """Você é um consultor estratégico sênior especializado em Empresas Juniores (EJs) do movimento \
empresa júnior brasileiro, com experiência em gestão, operações, gestão de projetos, desenvolvimento organizacional, \
vendas e marketing B2B, aprendizagem aplicada e transformação digital. Você escreve em português do Brasil, com tom \
profissional, direto e construtivo, para uma diretoria de EJ que precisa decidir o que fazer nos próximos 90 dias.

REGRAS INEGOCIÁVEIS:
1. Use SOMENTE as informações fornecidas (respostas, notas, indicadores, observações). NUNCA invente números, fatos, \
nomes, clientes, faturamentos ou resultados da EJ. Quando faltar informação para concluir algo, declare a limitação.
2. Não resuma apenas as respostas: interprete, conecte causas e consequências, aponte contradições e implicações.
3. Todas as recomendações devem seguir a lógica: problema -> causa provável -> ação -> resultado esperado -> indicador. \
Proíba-se escrever recomendações genéricas como "melhorar a comunicação".
4. Considere o contexto atual de mercado: pressão por produtividade, uso crescente de IA, automação, necessidade de \
eficiência, competição, diferenciação, geração de valor, formação profissional, conexão universidade-mercado, \
transformação digital, empregabilidade, networking e profissionalização da gestão. Relacione esse contexto à realidade \
da EJ sem inventar dados de mercado específicos.
5. Trate as observações da EJ como contexto qualitativo; use-as para qualificar ou questionar as pontuações.
6. Não use emojis. Não use tabelas Markdown. Use apenas títulos (##), subtítulos (###), listas com hífen e **negrito**.
7. Seja específico e conciso: prefira frases completas e acionáveis a jargão."""


# ------------------------------------------------------------------ chave de API
def obter_api_key() -> str | None:
    try:
        import streamlit as st
        chave = st.session_state.get("api_key_sessao")
        if chave:
            return chave.strip()
        try:
            chave = st.secrets.get("GEMINI_API_KEY")
        except Exception:  # secrets.toml ausente
            chave = None
        if chave:
            return str(chave).strip()
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    chave = os.getenv("GEMINI_API_KEY")
    return chave.strip() if chave else None


def api_configurada() -> bool:
    chave = obter_api_key()
    return bool(chave) and chave not in ("SUA_CHAVE", "SUA_CHAVE_AQUI")


# ---------------------------------------------------------------------- prompt
def _bloco_dimensoes(scores: dict) -> str:
    linhas = []
    for d in ORDEM_DIMENSOES:
        linhas.append(f"- {DIMENSOES[d]['nome']}: {scores['dim'][d]:.0f}/100 (peso no índice geral: {DIMENSOES[d]['peso']*100:.0f}%)")
        for sub, nota in scores["sub"].get(d, {}).items():
            linhas.append(f"    - {sub}: {nota:.0f}")
    return "\n".join(linhas)


def _bloco_indicadores(scores: dict) -> str:
    return "\n".join(f"- {cfg['nome']}: {scores['ind'][k]:.0f}/100" for k, cfg in INDICADORES.items())


def _bloco_lista(itens: list[dict]) -> str:
    return "\n".join(f"- {i['titulo']}: {i['texto']}" for i in itens) or "- (nenhum item identificado)"


def construir_prompt(ident: dict, observacoes: str, respostas: dict, scores: dict, diag: dict) -> str:
    resp = respostas_legiveis(respostas)
    bloco_resp = "\n".join(
        f"[{r['id']}] ({DIMENSOES[r['dim']]['curto']} / {r['sub']}) {r['pergunta']}\n    Resposta: " + " | ".join(r["respostas"])
        for r in resp
    )
    bloco_gargalos = "\n".join(
        f"- [{g['severidade'].upper()}] {g['titulo']}: {g['leitura']}" for g in diag["gargalos"]
    ) or "- Nenhum cruzamento crítico acionado pelas regras."
    bloco_acoes = "\n".join(
        f"- {a['prioridade']} | {a['nome_indicador']} (nota {a['nota']:.0f}, impacto {a['impacto']}, urgência {a['urgencia']}): {a['acao']}"
        for a in diag["acoes"]
    ) or "- Nenhuma ação crítica."
    sim = diag["simulacao_padrao"]
    return f"""Elabore o PARECER TÉCNICO do diagnóstico de maturidade da Empresa Júnior abaixo.

=== IDENTIFICAÇÃO ===
Nome: {ident.get('nome_ej', '-')}
Curso/área: {ident.get('curso', '-')} | Universidade: {ident.get('universidade', '-')} | Cidade: {ident.get('cidade', '-')}
Membros: {ident.get('n_membros', '-')} | Fundação: {ident.get('ano_fundacao', '-')} | Gestão: {ident.get('gestao', '-')}
Responsável: {ident.get('responsavel', '-')} ({ident.get('cargo', '-')})
Situação descrita pela EJ: {ident.get('situacao') or '(não informada)'}

=== PONTUAÇÕES (0-100) ===
Índice Geral de Maturidade: {scores['geral']:.0f}/100 — {scores['faixa']} (bruto {scores['geral_bruto']:.0f}, ajuste de elo mais fraco -{scores['ajuste']:.1f})
Perfil de equilíbrio entre dimensões: {scores['perfil']} (amplitude {scores['spread']:.0f} pontos)
Dimensões e subdimensões:
{_bloco_dimensoes(scores)}

=== INDICADORES ===
{_bloco_indicadores(scores)}

=== GARGALOS E CRUZAMENTOS IDENTIFICADOS PELO MOTOR DE REGRAS ===
{bloco_gargalos}

=== FORÇAS ===
{_bloco_lista(diag['forcas'])}
=== FRAGILIDADES ===
{_bloco_lista(diag['fragilidades'])}
=== RISCOS ===
{_bloco_lista(diag['riscos'])}
=== OPORTUNIDADES ===
{_bloco_lista(diag['oportunidades'])}

=== AÇÕES PRIORIZADAS PELO MOTOR (você pode refinar, reordenar e complementar) ===
{bloco_acoes}

=== SIMULAÇÃO CONCEITUAL: {sim['titulo']} (+{sim['pct']}%) ===
Veredito do motor: {sim['veredito']}
Pontos de gargalo: {', '.join(r['nome'] for r in sim['gargalos']) or 'nenhum'}

=== RESPOSTAS COMPLETAS ===
{bloco_resp}

=== OBSERVAÇÕES DA EJ (contexto qualitativo) ===
{observacoes.strip() or '(a EJ não registrou observações)'}

=== FORMATO OBRIGATÓRIO DA RESPOSTA ===
Produza exatamente estas seções, nesta ordem, com estes títulos de nível 2:

## 1. Resumo Executivo
(cerca de 1 página: onde a EJ está, por que está aqui e o que precisa fazer nos próximos 90 dias)
## 2. Diagnóstico Geral
(explique o nível de maturidade e o perfil de equilíbrio; não trate a classificação de forma simplista)
## 3. Processos e Saúde Operacional
(situação atual; principais gargalos; riscos; oportunidades)
## 4. Aprendizagem
(qualidade do desenvolvimento; hard skills; soft skills; aplicação prática; gestão do conhecimento)
## 5. Mercado e Comercial
(potencial; posicionamento; venda; ticket; networking; oportunidades)
## 6. Automação e Tecnologia
(maturidade; processos automatizáveis; integração; cultura de dados; capacitação; prontidão para IA)
## 7. Principais Forças
(Top 5, cada uma com uma explicação curta)
## 8. Principais Fragilidades
(Top 5)
## 9. Riscos Estratégicos
(Top 5, relacionando causa e consequência)
## 10. Oportunidades
(Top 5)
## 11. Plano de Ação
### Próximos 30 dias
### 60 dias
### 90 dias
Para CADA ação use exatamente os campos, em lista com hífen: **Ação**; **Problema e causa provável**; **Motivo**; \
**Impacto esperado**; **Dificuldade** (Baixa, Média ou Alta); **Responsável sugerido**; **Indicador de sucesso**.
## 12. Leitura das Observações e Limitações
(como as observações da EJ qualificam o diagnóstico; o que não foi possível concluir por falta de informação)

Seja específico: cada recomendação deve conectar problema, causa provável, ação, resultado esperado e indicador."""


# ------------------------------------------------------------------- chamada
def _mensagem_amigavel(exc: Exception) -> str:
    texto = str(exc).lower()
    if any(t in texto for t in ("api key", "api_key", "permission_denied", "unauthenticated", "401", "403")):
        return "A chave da API Gemini parece inválida ou sem permissão. Verifique o valor configurado em GEMINI_API_KEY."
    if any(t in texto for t in ("429", "quota", "resource_exhausted", "rate")):
        return "O limite de uso da API Gemini foi atingido. Aguarde alguns minutos e tente novamente."
    if any(t in texto for t in ("503", "unavailable", "overloaded", "timeout", "timed out", "deadline", "connection", "network")):
        return "O serviço Gemini está indisponível ou lento neste momento. Tente novamente em instantes."
    if any(t in texto for t in ("safety", "blocked")):
        return "A resposta foi bloqueada pelos filtros de segurança do Gemini. Revise o texto das observações e tente novamente."
    return "Não foi possível obter o parecer da IA neste momento."


def generate_ai_diagnosis(ident: dict, observacoes: str, respostas: dict, scores: dict, diag: dict) -> dict:
    """Gera o parecer de IA. Nunca lança exceção: retorna {'ok', 'texto', 'erro', 'modelo'}."""
    if not api_configurada():
        return {
            "ok": False, "texto": "", "modelo": None,
            "erro": "A chave GEMINI_API_KEY não está configurada. Veja o README para configurar o arquivo .streamlit/secrets.toml.",
        }
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return {"ok": False, "texto": "", "modelo": None,
                "erro": "A biblioteca google-genai não está instalada. Execute: pip install -r requirements.txt"}

    prompt = construir_prompt(ident, observacoes, respostas, scores, diag)
    ultimo_erro: Exception | None = None
    for modelo in GEMINI_MODELS:
        try:
            try:
                client = genai.Client(
                    api_key=obter_api_key(),
                    http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
                )
            except Exception:
                client = genai.Client(api_key=obter_api_key())
            resp = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.4,
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                ),
            )
            texto = (resp.text or "").strip()
            if len(texto) < 400:
                raise RuntimeError("Resposta vazia ou incompleta do modelo.")
            return {"ok": True, "texto": texto, "erro": None, "modelo": modelo}
        except Exception as exc:  # noqa: BLE001 - o app nunca deve quebrar por falha de API
            ultimo_erro = exc
            log.warning("Falha no modelo %s: %s", modelo, exc)
    return {
        "ok": False, "texto": "", "modelo": None,
        "erro": _mensagem_amigavel(ultimo_erro) if ultimo_erro else "Falha desconhecida ao chamar o Gemini.",
    }
