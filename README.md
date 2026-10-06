# NEJ POA — Diagnóstico de Maturidade EJ

Sistema em **Python + Streamlit** que diagnostica Empresas Juniores em 4 dimensões
(Processos, Aprendizagem, Mercado/Comercial, Automação/Tecnologia), calcula índices,
detecta gargalos, prioriza ações (plano 30/60/90), simula cenários "E se?" e gera
um **relatório PDF** com parecer opcional de IA (Google Gemini).

## Requisitos
- Python 3.11+ (testado em 3.12)
- VS Code (opcional)

## Instalação (Windows)
```bash
cd diagnostico_ej
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```
Linux/macOS: `source .venv/bin/activate` no lugar de `.venv\Scripts\activate`.

## Configurar o Gemini (opcional)
O diagnóstico e o PDF quantitativo funcionam **sem** chave. Para o parecer de IA:

1. Gere uma chave em https://aistudio.google.com/apikey
2. Crie `.streamlit/secrets.toml` (há um `secrets.toml.example`):
```toml
GEMINI_API_KEY="SUA_CHAVE"
```
Alternativa: copie `.env.example` para `.env`. Também é possível colar a chave na
barra lateral (fica só na memória da sessão).

Modelos usados: ver `GEMINI_MODELS` em `config/settings.py`.
Se a API falhar, o app mostra uma mensagem amigável e gera o relatório quantitativo.

## Estrutura
```
app.py                  entrada
config/                 settings (pesos, faixas, cores) e metodologia (indicadores, regras de gargalo, cenários)
data/perguntas.py       30 perguntas com pontuação
services/scoring.py     pergunta -> indicador -> dimensão -> índice geral
services/diagnostico.py gargalos, prioridades, plano 30/60/90, simulação
services/gemini.py      generate_ai_diagnosis()
services/pdf_generator.py  relatório PDF (ReportLab)
components/             sidebar, progresso, cards, gráficos Plotly, páginas
utils/                  helpers e validadores
assets/style.css        tema dark
```

## Metodologia (resumo)
`PERGUNTA -> INDICADOR -> DIMENSÃO -> MATURIDADE -> GARGALO -> PRIORIDADE -> RECOMENDAÇÃO`
- Cada pergunta vale 0–100 e alimenta indicadores; dimensões = média ponderada das perguntas.
- Índice Geral: Processos 30%, Mercado 30%, Aprendizagem 20%, Tecnologia 20%, com
  ajuste do "elo mais fraco" (dimensão < 40 desconta até 10 pontos).
- Detalhes comentados em `config/metodologia.py`.

## Privacidade
Nada é salvo em serviços externos. As respostas ficam na sessão; use
"Exportar progresso" para guardar em JSON. Só o parecer de IA envia dados ao Gemini,
e apenas quando você clica para gerá-lo.

## Integração futura com banco de dados
`utils/helpers.py::montar_payload()` define o payload serializável do diagnóstico;
basta persisti-lo/recuperá-lo em um repositório.
