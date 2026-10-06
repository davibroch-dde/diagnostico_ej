"""Relatório PDF em estilo consultoria (ReportLab). Gráficos desenhados nativamente (sem kaleido)."""
from __future__ import annotations

import io
import math
import re
from datetime import date

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

from config.metodologia import INDICADORES, INDICADORES_POR_DIMENSAO, INDICADORES_TRANSVERSAIS, PESO_ELO_MAIS_FRACO
from config.settings import DIMENSOES, ORDEM_DIMENSOES, faixa_de
from services.diagnostico import respostas_legiveis, simular

NAVY = colors.HexColor("#0B1020")
BLUE = colors.HexColor("#3B82F6")
PURPLE = colors.HexColor("#8B5CF6")
CYAN = colors.HexColor("#22D3EE")
GREEN = colors.HexColor("#10B981")
AMBER = colors.HexColor("#F59E0B")
RED = colors.HexColor("#EF4444")
ORANGE = colors.HexColor("#F97316")
INK = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F3F5FA")
LINE = colors.HexColor("#E2E6F0")

W, H = A4
MARGEM = 18 * mm
LARGURA = W - 2 * MARGEM

_SUBST = {"→": "->", "←": "<-", "≥": ">=", "≤": "<=", "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
          "…": "...", "•": "-", "×": "x", "◈": "", "◉": "", "◆": "", "⬡": "", "✓": "", "·": "-", "°": "o"}


def limpar(texto) -> str:
    """Remove caracteres fora do alfabeto suportado pelas fontes padrão do PDF."""
    t = "" if texto is None else str(texto)
    for k, v in _SUBST.items():
        t = t.replace(k, v)
    return t.encode("cp1252", errors="ignore").decode("cp1252")


def _esc(t) -> str:
    return limpar(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cor_nota(n: float):
    return RED if n <= 20 else ORANGE if n <= 40 else AMBER if n <= 60 else BLUE if n <= 80 else GREEN


def _hex(c) -> colors.Color:
    return colors.HexColor(c) if isinstance(c, str) else c


# ----------------------------------------------------------------------- estilos
def _estilos() -> dict[str, ParagraphStyle]:
    b = dict(fontName="Helvetica", textColor=INK, leading=14, fontSize=9.5, alignment=TA_LEFT)
    return {
        "corpo": ParagraphStyle("corpo", spaceAfter=5, **b),
        "pequeno": ParagraphStyle("pequeno", **{**b, "fontSize": 8.2, "leading": 11, "textColor": MUTED}),
        "h1": ParagraphStyle("h1", **{**b, "fontName": "Helvetica-Bold", "fontSize": 20, "leading": 24, "textColor": NAVY,
                                      "spaceBefore": 4, "spaceAfter": 8, "keepWithNext": 1}),
        "h2": ParagraphStyle("h2", **{**b, "fontName": "Helvetica-Bold", "fontSize": 13, "leading": 17, "textColor": BLUE,
                                      "spaceBefore": 10, "spaceAfter": 4, "keepWithNext": 1}),
        "h3": ParagraphStyle("h3", **{**b, "fontName": "Helvetica-Bold", "fontSize": 10.5, "leading": 14, "textColor": NAVY,
                                      "spaceBefore": 7, "spaceAfter": 3, "keepWithNext": 1}),
        "bullet": ParagraphStyle("bullet", leftIndent=12, bulletIndent=2, spaceAfter=3, **b),
        "bullet2": ParagraphStyle("bullet2", leftIndent=26, bulletIndent=16, spaceAfter=2, **{**b, "fontSize": 9}),
        "cel": ParagraphStyle("cel", **{**b, "fontSize": 8.6, "leading": 11.5}),
        "celb": ParagraphStyle("celb", **{**b, "fontSize": 8.6, "leading": 11.5, "fontName": "Helvetica-Bold"}),
        "capa_t": ParagraphStyle("capa_t", **{**b, "fontName": "Helvetica-Bold", "fontSize": 32, "leading": 38, "textColor": colors.white}),
        "capa_s": ParagraphStyle("capa_s", **{**b, "fontSize": 14, "leading": 19, "textColor": colors.HexColor("#B6C0DA")}),
        "capa_n": ParagraphStyle("capa_n", **{**b, "fontName": "Helvetica-Bold", "fontSize": 22, "leading": 28, "textColor": CYAN}),
        "capa_m": ParagraphStyle("capa_m", **{**b, "fontSize": 10.5, "leading": 15, "textColor": colors.HexColor("#8E9AB8")}),
    }


ST = _estilos()


def P(texto, estilo="corpo") -> Paragraph:
    return Paragraph(_esc(texto), ST[estilo])


def PR(markup, estilo="corpo") -> Paragraph:
    """Parágrafo com marcação ReportLab já segura."""
    return Paragraph(markup, ST[estilo])


# --------------------------------------------------------------- páginas (canvas)
def _capa(c, doc):
    c.saveState()
    c.setFillColor(colors.HexColor("#05070D"))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    for cx, cy, r, cor, a in ((W * 0.85, H * 0.88, 150, BLUE, 0.16), (W * 0.1, H * 0.12, 190, PURPLE, 0.14),
                              (W * 0.6, H * 0.45, 100, CYAN, 0.07)):
        for k in range(8, 0, -1):
            c.setFillColor(colors.Color(cor.red, cor.green, cor.blue, alpha=a / 8))
            c.circle(cx, cy, r * k / 8 * 1.4, stroke=0, fill=1)
    c.setFillColor(BLUE)
    c.roundRect(MARGEM, H - 40 * mm, 12 * mm, 12 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(MARGEM + 6 * mm, H - 36 * mm, "N")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGEM + 16 * mm, H - 35.5 * mm, "NEJ POA")
    c.setStrokeColor(CYAN)
    c.setLineWidth(2)
    c.line(MARGEM, 62 * mm, MARGEM + 40 * mm, 62 * mm)
    c.restoreState()


def _conteudo(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 11 * mm, W, 11 * mm, stroke=0, fill=1)
    c.setFillColor(BLUE)
    c.rect(0, H - 11 * mm, 30 * mm, 1.2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGEM, H - 7.2 * mm, "NEJ POA")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#B6C0DA"))
    c.drawRightString(W - MARGEM, H - 7.2 * mm, "Diagnostico de Maturidade da Empresa Junior")
    c.setStrokeColor(LINE)
    c.line(MARGEM, 14 * mm, W - MARGEM, 14 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.8)
    c.drawString(MARGEM, 9.5 * mm, limpar(f"{doc.nome_ej} - Relatorio gerado em {date.today():%d/%m/%Y}  |  Documento confidencial"))
    c.drawRightString(W - MARGEM, 9.5 * mm, f"Pagina {doc.page}")
    c.restoreState()


# ------------------------------------------------------------------ componentes
def secao(titulo: str, sub: str | None = None) -> list:
    itens = [P(titulo, "h1")]
    t = Table([[""]], colWidths=[LARGURA], rowHeights=[1.6])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BLUE)]))
    itens.append(t)
    itens.append(Spacer(1, 6))
    if sub:
        itens.append(P(sub, "pequeno"))
        itens.append(Spacer(1, 4))
    return itens


def cartoes(valores: list[tuple[str, str, colors.Color]], largura=LARGURA) -> Table:
    n = len(valores)
    gap = 3 * mm
    w = (largura - gap * (n - 1)) / n
    linha, larguras = [], []
    for i, (rot, val, cor) in enumerate(valores):
        tam = 22 if len(val) <= 8 else (13 if len(val) <= 14 else 10)
        cel = [PR(f'<font size="8" color="#6B7280">{_esc(rot.upper())}</font>'),
               PR(f'<font size="{tam}" color="{cor.hexval().replace("0x", "#")}"><b>{_esc(val)}</b></font>')]
        linha.append(cel)
        larguras.append(w)
        if i < n - 1:
            linha.append("")
            larguras.append(gap)
    t = Table([linha], colWidths=larguras)
    est = [("VALIGN", (0, 0), (-1, -1), "TOP")]
    for i in range(n):
        col = i * 2
        est += [("BACKGROUND", (col, 0), (col, 0), LIGHT), ("BOX", (col, 0), (col, 0), 0.6, LINE),
                ("LINEABOVE", (col, 0), (col, 0), 2.2, valores[i][2]),
                ("LEFTPADDING", (col, 0), (col, 0), 9), ("TOPPADDING", (col, 0), (col, 0), 8),
                ("BOTTOMPADDING", (col, 0), (col, 0), 8)]
    t.setStyle(TableStyle(est))
    return t


def barras(itens: list[tuple[str, float, colors.Color]], largura=LARGURA, altura_linha=15) -> Drawing:
    alt = altura_linha * len(itens) + 4
    d = Drawing(largura, alt)
    rotulo_w = largura * 0.40
    trilho = largura - rotulo_w - 34
    for i, (nome, val, cor) in enumerate(itens):
        y = alt - (i + 1) * altura_linha + 3
        d.add(String(0, y + 2, limpar(nome)[:48], fontName="Helvetica", fontSize=8.4, fillColor=INK))
        d.add(Rect(rotulo_w, y, trilho, 8, fillColor=colors.HexColor("#EDF0F7"), strokeColor=None))
        d.add(Rect(rotulo_w, y, max(1.5, trilho * val / 100), 8, fillColor=cor, strokeColor=None))
        d.add(String(rotulo_w + trilho + 6, y + 1, f"{val:.0f}", fontName="Helvetica-Bold", fontSize=8.6, fillColor=INK))
    return d


def radar(valores: dict[str, float], tamanho=240) -> Drawing:
    d = Drawing(tamanho + 80, tamanho + 30)
    cx, cy, r = (tamanho + 80) / 2, tamanho / 2 + 12, tamanho / 2 - 28
    nomes = list(valores)
    n = len(nomes)
    ang = [math.pi / 2 - 2 * math.pi * i / n for i in range(n)]
    for nivel in (20, 40, 60, 80, 100):
        pts = []
        for a in ang:
            pts += [cx + r * nivel / 100 * math.cos(a), cy + r * nivel / 100 * math.sin(a)]
        d.add(Polygon(pts, fillColor=None, strokeColor=colors.HexColor("#D5DAE8"), strokeWidth=0.6))
        d.add(String(cx + 2, cy + r * nivel / 100 + 1, str(nivel), fontName="Helvetica", fontSize=6, fillColor=MUTED))
    for a in ang:
        d.add(Line(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a), strokeColor=colors.HexColor("#D5DAE8"), strokeWidth=0.6))
    pts = []
    for a, nome in zip(ang, nomes):
        v = valores[nome]
        pts += [cx + r * v / 100 * math.cos(a), cy + r * v / 100 * math.sin(a)]
    d.add(Polygon(pts, fillColor=colors.Color(0.23, 0.51, 0.96, alpha=0.30), strokeColor=BLUE, strokeWidth=2))
    for a, nome in zip(ang, nomes):
        v = valores[nome]
        d.add(Circle(cx + r * v / 100 * math.cos(a), cy + r * v / 100 * math.sin(a), 3.2, fillColor=CYAN, strokeColor=BLUE))
        lx, ly = cx + (r + 16) * math.cos(a), cy + (r + 16) * math.sin(a)
        ancora = "middle" if abs(math.cos(a)) < 0.3 else ("start" if math.cos(a) > 0 else "end")
        d.add(String(lx, ly - 3, f"{limpar(nome)} ({v:.0f})", fontName="Helvetica-Bold", fontSize=8.5,
                     fillColor=NAVY, textAnchor=ancora))
    return d


def rosca(valor: float, cor, tamanho=130, rotulo="") -> Drawing:
    d = Drawing(tamanho, tamanho)
    c = tamanho / 2
    d.add(Wedge(c, c, c - 4, 0, 360, radius1=c - 18, fillColor=colors.HexColor("#E8ECF5"), strokeColor=None))
    if valor > 0:
        d.add(Wedge(c, c, c - 4, 90 - 359.9 * valor / 100, 90, radius1=c - 18, fillColor=cor, strokeColor=None))
    d.add(String(c, c - 4, f"{valor:.0f}", fontName="Helvetica-Bold", fontSize=30, fillColor=NAVY, textAnchor="middle"))
    d.add(String(c, c - 17, rotulo or "/100", fontName="Helvetica", fontSize=8, fillColor=MUTED, textAnchor="middle"))
    return d


def matriz(acoes: list[dict], largura=250, altura=230) -> Drawing:
    d = Drawing(largura + 40, altura + 36)
    ox, oy = 30, 24
    d.add(Rect(ox, oy, largura / 2, altura / 2, fillColor=colors.HexColor("#F5F8FF"), strokeColor=None))
    d.add(Rect(ox + largura / 2, oy + altura / 2, largura / 2, altura / 2, fillColor=colors.HexColor("#FEF1F1"), strokeColor=None))
    d.add(Rect(ox, oy + altura / 2, largura / 2, altura / 2, fillColor=colors.HexColor("#F1F5FE"), strokeColor=None))
    d.add(Rect(ox + largura / 2, oy, largura / 2, altura / 2, fillColor=colors.HexColor("#FFF8EA"), strokeColor=None))
    d.add(Rect(ox, oy, largura, altura, fillColor=None, strokeColor=colors.HexColor("#C9D0E2"), strokeWidth=0.8))
    d.add(Line(ox + largura / 2, oy, ox + largura / 2, oy + altura, strokeColor=colors.HexColor("#C9D0E2"), strokeDashArray=[2, 2]))
    d.add(Line(ox, oy + altura / 2, ox + largura, oy + altura / 2, strokeColor=colors.HexColor("#C9D0E2"), strokeDashArray=[2, 2]))
    d.add(String(ox + largura / 2, 8, "URGENCIA", fontName="Helvetica-Bold", fontSize=7.5, fillColor=MUTED, textAnchor="middle"))
    d.add(String(8, oy + altura / 2, "IMPACTO", fontName="Helvetica-Bold", fontSize=7.5, fillColor=MUTED, textAnchor="middle"))
    d.add(String(ox + largura - 4, oy + altura - 10, "AGIR AGORA", fontName="Helvetica-Bold", fontSize=7, fillColor=RED, textAnchor="end"))
    for n, a in enumerate(acoes, start=1):
        x = ox + largura * a["urgencia"] / 100
        y = oy + altura * a["impacto"] / 100
        d.add(Circle(x, y, 8, fillColor=_hex(a["cor"]), strokeColor=colors.white, strokeWidth=1))
        d.add(String(x, y - 3, str(n), fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.white, textAnchor="middle"))
    return d


def tabela(cabecalho: list[str], linhas: list[list], larguras: list[float], cores_linha=None) -> Table:
    dados = [[PR(f'<font color="white"><b>{_esc(c)}</b></font>', "cel") for c in cabecalho]]
    for ln in linhas:
        dados.append([c if hasattr(c, "wrap") else P(c, "cel") for c in ln])
    t = Table(dados, colWidths=larguras, repeatRows=1)
    est = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
           ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 5),
           ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6)]
    for i in range(2, len(dados), 2):
        est.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8F9FC")))
    t.setStyle(TableStyle(est))
    return t


def caixa(titulo: str, texto: str, cor) -> Table:
    c = _hex(cor)
    hexa = c.hexval().replace("0x", "#")
    t = Table([[[PR(f'<font size="7.5" color="{hexa}"><b>{_esc(titulo.upper())}</b></font>'), P(texto, "cel")]]],
              colWidths=[LARGURA])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("LINEBEFORE", (0, 0), (0, 0), 3, c),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


# ------------------------------------------------------- markdown (parecer de IA)
def _inline(t: str) -> str:
    t = _esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", t)
    return t.replace("`", "")


def markdown_para_fluxo(md: str) -> list:
    saida, tabela_buf = [], []

    def fechar_tabela():
        if not tabela_buf:
            return
        linhas = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in tabela_buf
                  if not re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", ln)]
        if linhas:
            ncol = max(len(l) for l in linhas)
            linhas = [l + [""] * (ncol - len(l)) for l in linhas]
            saida.append(tabela(linhas[0], [[PR(_inline(c), "cel") for c in l] for l in linhas[1:]], [LARGURA / ncol] * ncol))
            saida.append(Spacer(1, 6))
        tabela_buf.clear()

    for bruto in md.splitlines():
        ln = bruto.rstrip()
        if ln.strip().startswith("|"):
            tabela_buf.append(ln)
            continue
        fechar_tabela()
        s = ln.strip()
        if not s or re.match(r"^[-*_]{3,}$", s):
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            nivel = len(m.group(1))
            saida.append(PR(_inline(m.group(2)), {1: "h2", 2: "h2", 3: "h3", 4: "h3"}[nivel]))
            continue
        recuo = len(ln) - len(ln.lstrip())
        m = re.match(r"^[-*+]\s+(.*)", s)
        if m:
            saida.append(Paragraph(_inline(m.group(1)), ST["bullet2" if recuo >= 2 else "bullet"], bulletText="-" if recuo >= 2 else "\u2022"))
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)", s)
        if m:
            saida.append(Paragraph(_inline(m.group(2)), ST["bullet"], bulletText=f"{m.group(1)}."))
            continue
        saida.append(PR(_inline(s)))
    fechar_tabela()
    return saida


# ------------------------------------------------------------------- relatório
def _capa_story(ident: dict, scores: dict) -> list:
    return [
        Spacer(1, 62 * mm),
        P("Diagnóstico de Maturidade da Empresa Júnior", "capa_t"),
        Spacer(1, 10),
        P("Análise estratégica, operacional, comercial, de aprendizagem e de automação", "capa_s"),
        Spacer(1, 26 * mm),
        P(ident.get("nome_ej", "Empresa Júnior"), "capa_n"),
        Spacer(1, 4),
        P(f"{ident.get('curso', '')} - {ident.get('universidade', '')} - {ident.get('cidade', '')}", "capa_m"),
        P(f"Gestão {ident.get('gestao', '')}  |  Responsável: {ident.get('responsavel', '')} ({ident.get('cargo', '')})", "capa_m"),
        Spacer(1, 6),
        P(f"Emitido em {date.today():%d/%m/%Y}", "capa_m"),
        NextPageTemplate("conteudo"), PageBreak(),
    ]


def _pg_resumo(ident, scores, diag, ia_texto) -> list:
    s = secao("Resumo Executivo")
    rotulo, cor, leitura = faixa_de(scores["geral"])
    s.append(cartoes([("Índice Geral", f"{scores['geral']:.0f}/100", _hex(cor)), ("Maturidade", rotulo, _hex(cor)),
                      ("Perfil", scores["perfil"].replace("Moderadamente ", "Mod. "), BLUE)]))
    s.append(Spacer(1, 8))
    s.append(cartoes([(DIMENSOES[d]["curto"], f"{scores['dim'][d]:.0f}", _hex(DIMENSOES[d]["cor"])) for d in ORDEM_DIMENSOES]))
    s.append(Spacer(1, 10))
    pr = diag["principais"]
    for chave, titulo, cor_c in (("forca", "Principal força", GREEN), ("gargalo", "Principal gargalo", ORANGE),
                                 ("oportunidade", "Principal oportunidade", CYAN), ("risco", "Maior risco", RED)):
        s.append(caixa(f"{titulo}: {pr[chave]['titulo']}", pr[chave]["texto"], cor_c))
        s.append(Spacer(1, 4))
    s.append(Spacer(1, 4))
    s.append(P("Síntese quantitativa", "h2"))
    for par in diag["resumo"]:
        s.append(P(par))
    if ia_texto:
        s.append(P("O parecer técnico completo do consultor de IA está nas últimas páginas deste relatório.", "pequeno"))
    else:
        s.append(P("Atenção: o parecer de IA não foi gerado nesta emissão. Este relatório contém apenas a análise quantitativa.", "pequeno"))
    s.append(PageBreak())
    return s


def _pg_geral(scores) -> list:
    rotulo, cor, leitura = faixa_de(scores["geral"])
    s = secao("Índice Geral de Maturidade", "Média ponderada das dimensões, com ajuste do elo mais fraco.")
    topo = Table([[rosca(scores["geral"], _hex(cor), 150, rotulo),
                   [P(rotulo, "h2"), P(leitura), P(f"Perfil: {scores['perfil']} (amplitude de {scores['spread']:.0f} pontos entre dimensões).")]]],
                 colWidths=[55 * mm, LARGURA - 55 * mm])
    topo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    s += [topo, Spacer(1, 8), P("Matriz de maturidade", "h2")]
    s.append(barras([(DIMENSOES[d]["nome"], scores["dim"][d], _hex(DIMENSOES[d]["cor"])) for d in ORDEM_DIMENSOES], altura_linha=19))
    s.append(Spacer(1, 6))
    s.append(P("Composição do índice", "h2"))
    linhas = [[DIMENSOES[d]["nome"], f"{DIMENSOES[d]['peso']*100:.0f}%", f"{scores['dim'][d]:.0f}",
               f"{scores['dim'][d] * DIMENSOES[d]['peso']:.1f}"] for d in ORDEM_DIMENSOES]
    linhas.append(["Índice bruto (soma ponderada)", "100%", "-", f"{scores['geral_bruto']:.1f}"])
    linhas.append([f"Ajuste do elo mais fraco (dimensão abaixo de {PESO_ELO_MAIS_FRACO['limite']:.0f})", "-", "-", f"-{scores['ajuste']:.1f}"])
    linhas.append([PR("<b>Índice Geral de Maturidade</b>", "cel"), "", "", PR(f"<b>{scores['geral']:.1f}</b>", "cel")])
    s.append(tabela(["Dimensão", "Peso", "Nota", "Contribuição"], linhas, [LARGURA * 0.55, LARGURA * 0.13, LARGURA * 0.13, LARGURA * 0.19]))
    s.append(Spacer(1, 8))
    s.append(P("Faixas de maturidade: 0-20 Crítico | 21-40 Inicial | 41-60 Em desenvolvimento | 61-80 Estruturado | 81-100 Avançado. "
               "A classificação não substitui a leitura do perfil: duas EJs com a mesma nota podem ter prioridades muito diferentes.", "pequeno"))
    s.append(PageBreak())
    return s


def _pg_radar(scores, diag) -> list:
    s = secao("Radar de Maturidade e Matriz de Prioridades")
    vals = {DIMENSOES[d]["curto"]: scores["dim"][d] for d in ORDEM_DIMENSOES}
    s.append(Table([[radar(vals, 230), matriz(diag["acoes"][:12], 215, 210)]], colWidths=[LARGURA * 0.5, LARGURA * 0.5]))
    s.append(Spacer(1, 4))
    cor_prio = {"CRÍTICA": RED, "ALTA": ORANGE, "MÉDIA": AMBER, "BAIXA": GREEN}
    linhas = []
    for n, a in enumerate(diag["acoes"], start=1):
        linhas.append([str(n), a["nome_indicador"], str(a["impacto"]), str(a["urgencia"]),
                       PR(f'<font color="{cor_prio[a["prioridade"]].hexval().replace("0x", "#")}"><b>{_esc(a["prioridade"])}</b></font>', "cel")])
    if linhas:
        s.append(P("Ações priorizadas (impacto x urgência)", "h2"))
        s.append(tabela(["#", "Ação", "Impacto", "Urgência", "Prioridade"], linhas,
                        [LARGURA * 0.06, LARGURA * 0.50, LARGURA * 0.13, LARGURA * 0.13, LARGURA * 0.18]))
    s.append(PageBreak())
    return s


def _pg_dimensoes(scores) -> list:
    s = secao("Análise por Dimensão", "Subdimensões e indicadores derivados (0 a 100).")
    for d in ORDEM_DIMENSOES:
        cfg = DIMENSOES[d]
        rotulo, cor, _ = faixa_de(scores["dim"][d])
        bloco = [P(f"{cfg['nome']} - {scores['dim'][d]:.0f} ({rotulo})", "h2"), P(cfg["descricao"], "pequeno")]
        subs = [(k, v, cor_nota(v)) for k, v in scores["sub"].get(d, {}).items()]
        inds = [(INDICADORES[i]["nome"], scores["ind"][i], cor_nota(scores["ind"][i])) for i in INDICADORES_POR_DIMENSAO[d]]
        bloco += [P("Subdimensões", "h3"), barras(subs, altura_linha=14), P("Indicadores", "h3"), barras(inds, altura_linha=14), Spacer(1, 6)]
        s.append(KeepTogether(bloco))
    s.append(P("Indicadores transversais", "h2"))
    s.append(P("Cruzam perguntas de várias dimensões: escalabilidade, resiliência, conversão de conhecimento em valor, prontidão para IA e profissionalização.", "pequeno"))
    s.append(barras([(INDICADORES[i]["nome"], scores["ind"][i], cor_nota(scores["ind"][i])) for i in INDICADORES_TRANSVERSAIS], altura_linha=15))
    s.append(PageBreak())
    return s


def _lista_pdf(titulo: str, itens: list[dict], cor) -> list:
    s = [P(titulo, "h2")]
    for i in itens:
        nota = f" ({i['nota']:.0f})" if i.get("nota") is not None else ""
        s.append(caixa(f"{i['titulo']}{nota}", i["texto"], cor))
        s.append(Spacer(1, 3))
    return s


def _pg_gargalos(diag) -> list:
    s = secao("Gargalos e Análise Cruzada", "Onde a EJ está perdendo capacidade ao cruzar as dimensões.")
    if not diag["gargalos"]:
        s.append(P("Nenhum cruzamento crítico foi identificado."))
    for g in diag["gargalos"]:
        cor = RED if g["severidade"] == "alta" else AMBER
        s.append(KeepTogether([caixa(f"{g['titulo']} - severidade {g['severidade']}", g["leitura"] + " Consequência provável: " + g["consequencia"], cor), Spacer(1, 4)]))
    s.append(PageBreak())
    s += secao("Forças, Fragilidades, Riscos e Oportunidades")
    s += _lista_pdf("Principais forças", diag["forcas"], GREEN)
    s += _lista_pdf("Principais fragilidades", diag["fragilidades"], ORANGE)
    s += _lista_pdf("Riscos estratégicos", diag["riscos"], RED)
    s += _lista_pdf("Oportunidades", diag["oportunidades"], CYAN)
    s.append(PageBreak())
    return s


def _pg_plano(diag) -> list:
    s = secao("Plano de Ação 30 / 60 / 90 dias", "Cada ação segue a lógica problema, causa provável, ação, resultado esperado e indicador.")
    nomes = {30: "Próximos 30 dias - ações imediatas", 60: "60 dias - estruturação", 90: "90 dias - ações estratégicas"}
    for h in (30, 60, 90):
        s.append(P(nomes[h], "h2"))
        if not diag["plano"][h]:
            s.append(P("Nenhuma ação priorizada neste horizonte.", "pequeno"))
        for a in diag["plano"][h]:
            dados = [
                [PR(f'<b>{_esc(a["nome_indicador"])}</b>  -  prioridade {_esc(a["prioridade"])}', "cel"), ""],
                [P("Problema", "celb"), P(a["problema"], "cel")], [P("Causa provável", "celb"), P(a["causa"], "cel")],
                [P("Ação", "celb"), P(a["acao"], "cel")], [P("Resultado esperado", "celb"), P(a["resultado"], "cel")],
                [P("Indicador de sucesso", "celb"), P(a["indicador_sucesso"], "cel")],
                [P("Responsável / dificuldade", "celb"), P(f"{a['responsavel']} / {a['dificuldade']}", "cel")],
            ]
            t = Table(dados, colWidths=[LARGURA * 0.24, LARGURA * 0.76])
            t.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (-1, 0), _hex(a["cor"]).clone(alpha=0.18) if hasattr(_hex(a["cor"]), "clone") else LIGHT),
                                   ("BACKGROUND", (0, 1), (0, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                                   ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
            s += [KeepTogether([t, Spacer(1, 6)])]
    s.append(PageBreak())
    return s


def _pg_simulacao(scores) -> list:
    s = secao("Análise \"E se?\"", "Simulação conceitual baseada nos indicadores do diagnóstico; não é uma previsão numérica.")
    for cen, pct in (("volume", 30), ("comercial", 20), ("saida", 30)):
        sim = simular(scores, cen, pct)
        cor = {"ok": GREEN, "atencao": AMBER, "critico": RED}[sim["nivel"]]
        bloco = [caixa(sim["pergunta"], sim["veredito"], cor), Spacer(1, 3)]
        if sim["gargalos"] or sim["atencao"]:
            linhas = [[r["nome"], f"{r['nota']:.0f}", f"{r['exigido']:.0f}", r["status"]] for r in sim["linhas"] if r["status"] != "Suporta"]
            bloco.append(tabela(["Indicador", "Nota atual", "Nível exigido", "Status"], linhas,
                                [LARGURA * 0.5, LARGURA * 0.16, LARGURA * 0.18, LARGURA * 0.16]))
        bloco.append(Spacer(1, 8))
        s.append(KeepTogether(bloco))
    s.append(P(simular(scores, "volume", 30)["nota_metodologica"], "pequeno"))
    s.append(PageBreak())
    return s


def _pg_parecer(ia_texto) -> list:
    s = secao("Parecer Técnico do Consultor de IA", "Gerado pelo Google Gemini a partir das respostas, notas e observações. Revise antes de compartilhar.")
    if ia_texto:
        s += markdown_para_fluxo(ia_texto)
    else:
        s.append(caixa("Parecer de IA não gerado", "A API do Gemini estava indisponível ou não configurada nesta emissão. "
                       "As análises quantitativas deste relatório permanecem válidas.", AMBER))
    s.append(PageBreak())
    return s


def _pg_observacoes(ident, observacoes, respostas) -> list:
    s = secao("Observações da EJ e Contexto")
    s.append(P("Situação descrita pela EJ", "h2"))
    s.append(P(ident.get("situacao") or "Não informada."))
    s.append(P("Observações registradas", "h2"))
    s.append(P(observacoes.strip() or "A EJ não registrou observações."))
    s.append(P("Dados de identificação", "h2"))
    linhas = [["Nome", ident.get("nome_ej", "")], ["Curso", ident.get("curso", "")], ["Universidade", ident.get("universidade", "")],
              ["Cidade", ident.get("cidade", "")], ["Membros", str(ident.get("n_membros", ""))], ["Fundação", str(ident.get("ano_fundacao", ""))],
              ["Responsável", f"{ident.get('responsavel', '')} ({ident.get('cargo', '')})"], ["Gestão", ident.get("gestao", "")]]
    s.append(tabela(["Campo", "Informação"], linhas, [LARGURA * 0.25, LARGURA * 0.75]))
    s.append(PageBreak())
    s += secao("Anexo - Respostas do Questionário")
    for r in respostas_legiveis(respostas):
        s.append(KeepTogether([PR(f"<b>{r['id']}</b> - {_esc(r['pergunta'])}", "cel"),
                               PR("<i>" + _esc(" | ".join(r["respostas"])) + "</i>", "pequeno"), Spacer(1, 4)]))
    s.append(Spacer(1, 8))
    s.append(P("Metodologia: pergunta -> indicador -> dimensão -> maturidade -> gargalo -> prioridade -> recomendação. "
               "Notas de 0 a 100 por pergunta, ponderadas por peso; índice geral com pesos por dimensão e ajuste do elo mais fraco.", "pequeno"))
    return s


def gerar_pdf(ident: dict, observacoes: str, respostas: dict, scores: dict, diag: dict, ia_texto: str | None) -> bytes:
    """Gera o relatório e devolve os bytes do PDF."""
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, title=limpar(f"Diagnostico de Maturidade - {ident.get('nome_ej', '')}"),
                          author="NEJ POA", leftMargin=MARGEM, rightMargin=MARGEM, topMargin=20 * mm, bottomMargin=20 * mm)
    doc.nome_ej = limpar(ident.get("nome_ej", "Empresa Junior"))
    f_capa = Frame(MARGEM, 20 * mm, LARGURA, H - 40 * mm, id="capa", leftPadding=0, rightPadding=0)
    f_cont = Frame(MARGEM, 20 * mm, LARGURA, H - 40 * mm, id="cont", leftPadding=0, rightPadding=0)
    doc.addPageTemplates([PageTemplate("capa", [f_capa], onPage=_capa), PageTemplate("conteudo", [f_cont], onPage=_conteudo)])
    story = []
    story += _capa_story(ident, scores)
    story += _pg_resumo(ident, scores, diag, ia_texto)
    story += _pg_geral(scores)
    story += _pg_radar(scores, diag)
    story += _pg_dimensoes(scores)
    story += _pg_gargalos(diag)
    story += _pg_plano(diag)
    story += _pg_simulacao(scores)
    story += _pg_parecer(ia_texto)
    story += _pg_observacoes(ident, observacoes, respostas)
    doc.build(story)
    return buf.getvalue()
