"""Configurações globais, identidade visual e parâmetros do diagnóstico."""
from __future__ import annotations

APP_NAME = "NEJ POA — Diagnóstico de Maturidade EJ"
APP_SHORT = "NEJ POA"
APP_SUBTITLE = "Diagnóstico de Maturidade de Empresas Juniores"
APP_VERSION = "1.0"

# Modelos Gemini tentados em ordem (o segundo é fallback caso o primeiro falhe).
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]
GEMINI_TIMEOUT_MS = 150_000
GEMINI_MAX_OUTPUT_TOKENS = 12_000

# Paleta (usada em gráficos Streamlit/Plotly e no PDF)
COR = {
    "bg": "#05070D",
    "card": "#0B1020",
    "card2": "#111833",
    "borda": "#1E2747",
    "texto": "#E6EAF5",
    "muted": "#8E9AB8",
    "azul": "#3B82F6",
    "roxo": "#8B5CF6",
    "ciano": "#22D3EE",
    "verde": "#10B981",
    "amarelo": "#F59E0B",
    "vermelho": "#EF4444",
}

# Dimensões principais. O peso entra no Índice Geral (ver config/metodologia.py).
DIMENSOES = {
    "processos": {
        "nome": "Processos e Saúde Operacional",
        "curto": "Processos",
        "glifo": "◈",
        "cor": COR["azul"],
        "peso": 0.30,
        "etapa": "01",
        "descricao": "Padronização, organização, gestão de projetos e capacidade de execução sem sobrecarga.",
    },
    "aprendizagem": {
        "nome": "Aprendizagem e Desenvolvimento",
        "curto": "Aprendizagem",
        "glifo": "◉",
        "cor": COR["roxo"],
        "peso": 0.20,
        "etapa": "02",
        "descricao": "Transformação de formação em capacidade real de gerar soluções para o mercado.",
    },
    "mercado": {
        "nome": "Mercado, Setor e Desenvolvimento Comercial",
        "curto": "Mercado",
        "glifo": "◆",
        "cor": COR["ciano"],
        "peso": 0.30,
        "etapa": "03",
        "descricao": "Da atratividade do mercado ao fechamento: posicionamento, venda, ticket e networking.",
    },
    "automacao": {
        "nome": "Automação, Tecnologia e Sistematização",
        "curto": "Tecnologia",
        "glifo": "⬡",
        "cor": COR["verde"],
        "peso": 0.20,
        "etapa": "04",
        "descricao": "Maturidade sistêmica: ferramentas integradas, automação, dados e preparo para IA.",
    },
}
ORDEM_DIMENSOES = ["processos", "aprendizagem", "mercado", "automacao"]

# Faixas de maturidade: (limite superior inclusivo, rótulo, cor, leitura)
FAIXAS = [
    (20, "CRÍTICO", COR["vermelho"],
     "A EJ opera sem base estruturada. O foco deve ser estabilizar o essencial antes de buscar crescimento."),
    (40, "INICIAL", "#F97316",
     "Há iniciativas válidas, porém dependentes de pessoas e de esforço individual. É hora de transformar prática em padrão."),
    (60, "EM DESENVOLVIMENTO", COR["amarelo"],
     "Existem bases importantes, mas com inconsistências. O desafio é dar regularidade e fechar as lacunas mais críticas."),
    (80, "ESTRUTURADO", COR["azul"],
     "A EJ tem boa estrutura. O desafio passa a ser consistência, medição e capacidade de escalar com qualidade."),
    (100, "AVANÇADO", COR["verde"],
     "Operação madura. O foco é eficiência, inovação e consolidar-se como referência no ecossistema."),
]


def faixa_de(nota: float) -> tuple[str, str, str]:
    """Retorna (rótulo, cor, leitura) para uma nota 0–100."""
    n = round(nota)
    for limite, rotulo, cor, leitura in FAIXAS:
        if n <= limite:
            return rotulo, cor, leitura
    return FAIXAS[-1][1], FAIXAS[-1][2], FAIXAS[-1][3]


# Classificação de prioridade (score = 0,55*impacto + 0,45*urgência)
PRIORIDADES = [
    (72, "CRÍTICA", COR["vermelho"]),
    (58, "ALTA", "#F97316"),
    (42, "MÉDIA", COR["amarelo"]),
    (0, "BAIXA", COR["verde"]),
]

CAMPOS_IDENTIFICACAO = [
    ("nome_ej", "Nome da Empresa Júnior"),
    ("curso", "Curso / área principal"),
    ("universidade", "Universidade"),
    ("cidade", "Cidade"),
    ("n_membros", "Número atual de membros"),
    ("ano_fundacao", "Ano de fundação"),
    ("responsavel", "Presidente / responsável pelo preenchimento"),
    ("cargo", "Cargo do responsável"),
    ("gestao", "Período / gestão atual"),
]
