"""Regras de diagnóstico: gargalos, forças, riscos, prioridades, plano 30/60/90 e simulação.

Transforma as notas calculadas em decisão gerencial, seguindo a cadeia
INDICADOR -> GARGALO -> PRIORIDADE -> RECOMENDAÇÃO.
"""
from __future__ import annotations

from config.metodologia import CENARIOS, INDICADORES, REGRAS_GARGALO
from config.settings import DIMENSOES, ORDEM_DIMENSOES, PRIORIDADES
from data.perguntas import PERGUNTAS_POR_ID

LIMITE_FORCA = 65
LIMITE_FRAGILIDADE = 55
LIMITE_ACAO = 70
MAX_ACOES = 12
MAX_POR_HORIZONTE = 4


# ------------------------------------------------------------------ gargalos
def detectar_gargalos(scores: dict) -> list[dict]:
    """Aplica as regras de análise cruzada e devolve os gargalos identificados."""
    i, d, q = scores["ind"], scores["dim"], scores["q"]
    nomes = {k: DIMENSOES[k]["curto"] for k in ORDEM_DIMENSOES}
    maior = max(d, key=d.get)
    menor = min(d, key=d.get)
    fmt = {"maior": f"{nomes[maior]}: {d[maior]:.0f}", "menor": f"{nomes[menor]}: {d[menor]:.0f}"}
    achados = []
    for regra in REGRAS_GARGALO:
        try:
            ativa = bool(regra["cond"](i, d, q))
        except KeyError:
            ativa = False
        if ativa:
            achados.append({
                "id": regra["id"],
                "severidade": regra["severidade"],
                "titulo": regra["titulo"],
                "leitura": regra["leitura"].format(**fmt),
                "consequencia": regra["consequencia"],
                "foco": regra["foco"],
            })
    ordem = {"alta": 0, "média": 1, "baixa": 2}
    achados.sort(key=lambda g: ordem.get(g["severidade"], 3))
    return achados


# ------------------------------------------------------------------ prioridades
def classificar_prioridade(valor: float) -> tuple[str, str]:
    for limite, rotulo, cor in PRIORIDADES:
        if valor >= limite:
            return rotulo, cor
    return PRIORIDADES[-1][1], PRIORIDADES[-1][2]


def gerar_acoes(scores: dict, gargalos: list[dict]) -> list[dict]:
    """Gera a lista de ações recomendadas, com impacto, urgência e prioridade."""
    foco_alto = {ind for g in gargalos if g["severidade"] == "alta" for ind in g["foco"]}
    foco_medio = {ind for g in gargalos if g["severidade"] != "alta" for ind in g["foco"]}
    acoes = []
    for ind, cfg in INDICADORES.items():
        nota = scores["ind"][ind]
        if nota >= LIMITE_ACAO:
            continue
        lacuna = (100 - nota) / 100
        impacto = cfg["impacto"] * (0.45 + 0.55 * lacuna)
        urgencia = cfg["urgencia"] * (0.35 + 0.65 * lacuna)
        if ind in foco_alto:
            urgencia += 12
            impacto += 4
        elif ind in foco_medio:
            urgencia += 6
        impacto = round(min(100, impacto))
        urgencia = round(min(100, urgencia))
        score = 0.55 * impacto + 0.45 * urgencia
        prioridade, cor = classificar_prioridade(score)
        acoes.append({
            "indicador": ind, "nome_indicador": cfg["nome"], "nota": nota,
            "impacto": impacto, "urgencia": urgencia, "score": round(score, 1),
            "prioridade": prioridade, "cor": cor,
            "problema": cfg["problema"], "causa": cfg["causa"], "acao": cfg["acao"],
            "resultado": cfg["resultado"], "indicador_sucesso": cfg["indicador"],
            "responsavel": cfg["responsavel"], "dificuldade": cfg["dificuldade"],
            "horizonte": cfg["horizonte"], "oportunidade": cfg["oportunidade"],
            "risco": cfg["risco"], "gargalo_relacionado": ind in foco_alto,
        })
    acoes.sort(key=lambda a: a["score"], reverse=True)
    return acoes[:MAX_ACOES]


def montar_plano(acoes: list[dict]) -> dict[int, list[dict]]:
    """Distribui as ações em 30/60/90 dias respeitando o horizonte natural de cada uma."""
    plano: dict[int, list[dict]] = {30: [], 60: [], 90: []}
    excedentes = []
    for a in acoes:
        h = a["horizonte"]
        if len(plano[h]) < MAX_POR_HORIZONTE:
            plano[h].append(a)
        else:
            excedentes.append(a)
    for a in excedentes:  # transborda para o horizonte seguinte
        for h in (60, 90):
            if h >= a["horizonte"] and len(plano[h]) < MAX_POR_HORIZONTE:
                plano[h].append(a)
                break
    # Garante que 30 dias nunca fique vazio quando há ações em outros horizontes
    if not plano[30]:
        for h in (60, 90):
            if len(plano[h]) > 1:
                plano[30].append(plano[h].pop(0))
                break
    return plano


# --------------------------------------------------------------- forças e riscos
def _top_forcas(scores: dict) -> list[dict]:
    itens = sorted(scores["ind"].items(), key=lambda kv: kv[1], reverse=True)
    fortes = [(k, v) for k, v in itens if v >= LIMITE_FORCA][:5]
    if len(fortes) < 3:  # garante ao menos 3 itens com a melhor leitura disponível
        fortes = itens[:3]
    return [{"titulo": INDICADORES[k]["nome"], "texto": INDICADORES[k]["forca"], "nota": v} for k, v in fortes]


def _top_fragilidades(scores: dict) -> list[dict]:
    itens = sorted(scores["ind"].items(), key=lambda kv: kv[1])
    fracos = [(k, v) for k, v in itens if v < LIMITE_FRAGILIDADE][:5]
    if len(fracos) < 3:
        fracos = itens[:3]
    return [{"titulo": INDICADORES[k]["nome"], "texto": INDICADORES[k]["fragilidade"], "nota": v} for k, v in fracos]


def _top_riscos(scores: dict, gargalos: list[dict]) -> list[dict]:
    riscos, vistos = [], set()
    for g in gargalos:
        if g["severidade"] == "alta" and g["titulo"] not in vistos:
            riscos.append({"titulo": g["titulo"], "texto": g["consequencia"], "nota": None})
            vistos.add(g["titulo"])
    pesos = sorted(
        ((k, (100 - v) * INDICADORES[k]["impacto"] / 100) for k, v in scores["ind"].items() if v < 50),
        key=lambda kv: kv[1], reverse=True,
    )
    for k, _ in pesos:
        if len(riscos) >= 5:
            break
        riscos.append({"titulo": INDICADORES[k]["nome"], "texto": INDICADORES[k]["risco"], "nota": scores["ind"][k]})
    if not riscos:
        menor = min(scores["ind"], key=scores["ind"].get)
        riscos.append({"titulo": INDICADORES[menor]["nome"], "texto": INDICADORES[menor]["risco"], "nota": scores["ind"][menor]})
    return riscos[:5]


def _top_oportunidades(acoes: list[dict]) -> list[dict]:
    ordenadas = sorted(acoes, key=lambda a: a["impacto"], reverse=True)[:5]
    return [{"titulo": a["nome_indicador"], "texto": a["oportunidade"], "nota": a["nota"]} for a in ordenadas]


# ------------------------------------------------------------------- principal
def _principais(scores: dict, gargalos: list[dict], acoes: list[dict], forcas: list[dict], riscos: list[dict]) -> dict:
    forca = forcas[0]
    if gargalos:
        g = gargalos[0]
        gargalo = {"titulo": g["titulo"], "texto": g["leitura"]}
    elif acoes:
        a = acoes[0]
        gargalo = {"titulo": a["nome_indicador"], "texto": a["problema"]}
    else:
        gargalo = {"titulo": "Sem gargalo crítico", "texto": "Nenhum cruzamento crítico foi identificado nas respostas."}
    if acoes:
        a = max(acoes, key=lambda x: x["impacto"])
        oport = {"titulo": a["nome_indicador"], "texto": a["oportunidade"]}
    else:
        oport = {"titulo": "Consolidar a excelência", "texto": "Todos os indicadores estão em nível elevado; o foco é inovação e referência."}
    risco = riscos[0]
    return {"forca": forca, "gargalo": gargalo, "oportunidade": oport, "risco": risco}


# ----------------------------------------------------------------------- resumo
def resumo_deterministico(ident: dict, scores: dict, diag: dict) -> list[str]:
    """Resumo executivo quantitativo (usado quando o parecer de IA não está disponível)."""
    d = scores["dim"]
    maior = max(d, key=d.get)
    menor = min(d, key=d.get)
    nome = ident.get("nome_ej") or "A EJ"
    p1 = (
        f"{nome} apresenta Índice Geral de Maturidade de {scores['geral']:.0f}/100, classificado como "
        f"{scores['faixa']}. {scores['leitura']} O perfil é {scores['perfil'].lower()}: a dimensão mais madura é "
        f"{DIMENSOES[maior]['curto']} ({d[maior]:.0f}) e a menos madura é {DIMENSOES[menor]['curto']} ({d[menor]:.0f})."
    )
    if scores["ajuste"] > 0:
        p1 += (
            f" Foi aplicado um desconto de {scores['ajuste']:.1f} ponto(s) pelo elo mais fraco, pois uma dimensão "
            "abaixo de 40 limita o desempenho do conjunto."
        )
    pr = diag["principais"]
    p2 = (
        f"Principal força: {pr['forca']['titulo']}. Principal gargalo: {pr['gargalo']['titulo']}. "
        f"Principal oportunidade: {pr['oportunidade']['titulo']}. Maior risco: {pr['risco']['titulo']}."
    )
    topo = [a["nome_indicador"] for a in diag["acoes"][:3]]
    p3 = (
        "Prioridades para os próximos 90 dias: " + "; ".join(topo) + "."
        if topo else "Não há ações críticas; a prioridade é manter e documentar as boas práticas."
    )
    return [p1, p2, p3]


# ---------------------------------------------------------------------- análise
def analisar(ident: dict, scores: dict) -> dict:
    gargalos = detectar_gargalos(scores)
    acoes = gerar_acoes(scores, gargalos)
    forcas = _top_forcas(scores)
    fragilidades = _top_fragilidades(scores)
    riscos = _top_riscos(scores, gargalos)
    oportunidades = _top_oportunidades(acoes)
    diag = {
        "gargalos": gargalos,
        "acoes": acoes,
        "plano": montar_plano(acoes),
        "forcas": forcas,
        "fragilidades": fragilidades,
        "riscos": riscos,
        "oportunidades": oportunidades,
        "principais": _principais(scores, gargalos, acoes, forcas, riscos),
        "simulacao_padrao": simular(scores, "volume", 30),
    }
    diag["resumo"] = resumo_deterministico(ident, scores, diag)
    return diag


# ------------------------------------------------------------------- simulação
def simular(scores: dict, cenario: str, pct: int) -> dict:
    """Simulação conceitual "E se?" baseada exclusivamente nos indicadores do diagnóstico."""
    cfg = CENARIOS[cenario]
    linhas = []
    for ind, base, k in cfg["exigencias"]:
        exigido = min(95.0, base + k * pct)
        nota = scores["ind"][ind]
        margem = nota - exigido
        status = "Gargalo" if margem < 0 else ("Atenção" if margem < 8 else "Suporta")
        linhas.append({
            "indicador": ind, "nome": INDICADORES[ind]["nome"], "nota": nota,
            "exigido": round(exigido, 1), "margem": round(margem, 1), "status": status,
        })
    linhas.sort(key=lambda r: r["margem"])
    gargalos = [r for r in linhas if r["status"] == "Gargalo"]
    atencao = [r for r in linhas if r["status"] == "Atenção"]
    if not gargalos and len(atencao) <= 1:
        veredito, nivel = "A estrutura atual provavelmente suportaria esse cenário.", "ok"
    elif len(gargalos) <= 2:
        veredito, nivel = "A estrutura suportaria apenas parcialmente: há pontos que precisam de reforço antes.", "atencao"
    else:
        veredito, nivel = "A estrutura atual provavelmente não suportaria esse cenário sem ajustes prévios.", "critico"
    return {
        "cenario": cenario, "titulo": cfg["titulo"], "pct": pct,
        "pergunta": cfg["pergunta"].format(pct=pct),
        "linhas": linhas, "gargalos": gargalos, "atencao": atencao,
        "veredito": veredito, "nivel": nivel,
        "nota_metodologica": (
            "Simulação conceitual baseada nos indicadores do diagnóstico: compara a nota atual de cada "
            "indicador com o nível mínimo estimado para sustentar o cenário. Não é uma previsão numérica "
            "de resultados e não utiliza dados externos à EJ."
        ),
    }


def respostas_legiveis(respostas: dict) -> list[dict]:
    """Lista as respostas em texto (usada no prompt de IA e no anexo do PDF)."""
    saida = []
    for qid, q in PERGUNTAS_POR_ID.items():
        r = respostas.get(qid)
        if r is None or r == []:
            continue
        ids = r if isinstance(r, list) else [r]
        textos = [o["texto"] for o in q["opcoes"] if o["id"] in ids]
        saida.append({"id": qid, "dim": q["dim"], "sub": q["sub"], "pergunta": q["texto"], "respostas": textos})
    return saida
