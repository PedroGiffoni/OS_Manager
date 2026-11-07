from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.dml.color import RGBColor as SlideColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches as SlideInches, Pt as SlidePt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as PDFImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table as PDFTable, TableStyle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "ESTUDO_REQUISITOS_GESTAO_DE_DEMANDAS_V1.md"
OUT = ROOT / "docs" / "estudo-requisitos"
MEDIA = ROOT / "docs" / "media"
ASSETS = ROOT / "backend" / "app" / "report_assets"
LOGO = ASSETS / "sebrae-cor.png"
BLUE = "005EB8"
INK = "14223A"
MUTED = "52647C"
PALE = "F0F8FE"
WHITE = "FFFFFF"


def parse_blocks(markdown: str):
    lines = markdown.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            table = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[\s:|-]+", c or "-") for c in row):
                    table.append(row)
                i += 1
            out.append(("table", table))
            continue
        if line.startswith("#"):
            n = len(line) - len(line.lstrip("#"))
            out.append(("heading", (n, line[n:].strip())))
            i += 1
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append(("bullet", items))
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                items.append(re.sub(r"^\d+\. ", "", lines[i].strip()))
                i += 1
            out.append(("number", items))
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("#", "-", "|")) and not re.match(r"^\d+\. ", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append(("paragraph", " ".join(para)))
    return out


def plain(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    tick = chr(96)
    return re.sub(tick + r"([^" + tick + r"]*)" + tick, r"\1", text)


def rich_reportlab(text: str) -> str:
    safe = escape(text)
    safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)
    tick = chr(96)
    return re.sub(tick + r"([^" + tick + r"]*)" + tick, r'<font name="Figtree">\1</font>', safe)


def build_docx(blocks):
    doc = Document()
    section = doc.sections[0]
    section.top_margin, section.bottom_margin = Inches(.72), Inches(.68)
    section.left_margin = section.right_margin = Inches(.78)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Figtree", Pt(10)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after, normal.paragraph_format.line_spacing = Pt(6), 1.12
    for name, size in (("Heading 1", 18), ("Heading 2", 13), ("Heading 3", 11)):
        style = doc.styles[name]
        style.font.name, style.font.size, style.font.bold = "Figtree", Pt(size), True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 9)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True
    header = section.header.paragraphs[0]
    r = header.add_run("GESTÃO DE DEMANDAS     |     ESTUDO DE REQUISITOS")
    r.font.name, r.font.size, r.font.color.rgb = "Lato", Pt(8), RGBColor.from_string(BLUE)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = footer.add_run("Versão 1.0  ·  06/11/2026     |     Página ")
    r.font.name, r.font.size, r.font.color.rgb = "Lato", Pt(8), RGBColor.from_string(MUTED)
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer._p.append(fld)
    if LOGO.exists():
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(60)
        p.add_run().add_picture(str(LOGO), width=Inches(1.45))
    p = doc.add_paragraph(style="Title")
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(22), Pt(9)
    r = p.add_run("Estudo de requisitos\nGestão de Demandas")
    r.font.name, r.font.size, r.font.bold = "Figtree", Pt(30), True
    r.font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph()
    r = p.add_run("Base de validação com o setor e especificação para o desenvolvimento definitivo")
    r.font.name, r.font.size, r.font.color.rgb = "Lato", Pt(13), RGBColor.from_string(MUTED)
    p.paragraph_format.space_after = Pt(28)
    p = doc.add_paragraph()
    r = p.add_run("Versão 1.0  ·  06 de novembro de 2026\nProtótipo funcional para descoberta e testes internos")
    r.font.name, r.font.size, r.font.color.rgb = "Figtree", Pt(11), RGBColor.from_string(INK)
    p.paragraph_format.space_after = Pt(22)
    p = doc.add_paragraph()
    r = p.add_run("Este documento descreve o retrato local do projeto e diferencia funções encontradas de decisões ainda sujeitas a validação. Alterações recentes de histórico, horas e relatórios permanecem locais e não devem ser presumidas na publicação atual.")
    r.font.name, r.font.size, r.font.color.rgb = "Figtree", Pt(10), RGBColor.from_string(MUTED)
    doc.add_page_break()

    started = False
    for typ, value in blocks:
        if typ == "heading" and value[1].startswith("Estudo de requisitos da Gestão de Demandas"):
            continue
        if typ == "paragraph" and value.startswith("**Versão 1.0"):
            continue
        if typ == "heading" and value[1] == "1. Síntese executiva":
            started = True
        if not started:
            continue
        if typ == "heading":
            n, text = value
            doc.add_heading(plain(text), level=min(max(n, 1), 3))
        elif typ == "paragraph":
            p = doc.add_paragraph()
            p.paragraph_format.widow_control = True
            tick = chr(96)
            for piece in re.split(r"(\*\*.*?\*\*|" + tick + r".*?" + tick + r")", value):
                if piece:
                    bold = piece.startswith("**") and piece.endswith("**")
                    code = piece.startswith(tick) and piece.endswith(tick)
                    text = piece[2:-2] if bold or code else piece
                    r = p.add_run(text)
                    r.bold, r.font.name = bold, "Consolas" if code else "Figtree"
                    if code:
                        r.font.size = Pt(9)
        elif typ in ("bullet", "number"):
            for item in value:
                p = doc.add_paragraph(style="List Bullet" if typ == "bullet" else "List Number")
                p.paragraph_format.space_after = Pt(3)
                p.add_run(plain(item))
        elif typ == "table":
            rows = value
            if not rows:
                continue
            ncols = max(map(len, rows))
            table = doc.add_table(rows=0, cols=ncols)
            table.style, table.autofit = "Table Grid", False
            usable = 6.9
            weights = {2: [1.5, 5.4], 3: [1.15, 2.65, 3.1], 4: [.48, 3.2, 1.15, 2.07]}.get(ncols, [usable/ncols]*ncols)
            widths = [Inches(w * usable / sum(weights)) for w in weights]
            for ri, row in enumerate(rows):
                cells = table.add_row().cells
                for ci in range(ncols):
                    cell = cells[ci]
                    cell.width = widths[ci]
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    cell.text = ""
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.line_spacing = 1.0
                    for piece in re.split(r"(\*\*.*?\*\*)", row[ci] if ci < len(row) else ""):
                        if piece:
                            rr = p.add_run(plain(piece))
                            rr.bold = (piece.startswith("**") and piece.endswith("**")) or ri == 0
                            rr.font.name, rr.font.size = "Figtree", Pt(8.3)
                            rr.font.color.rgb = RGBColor.from_string(WHITE if ri == 0 else INK)
                    if ri == 0:
                        shd = OxmlElement("w:shd")
                        shd.set(qn("w:fill"), BLUE)
                        cell._tc.get_or_add_tcPr().append(shd)
                if ri == 0:
                    trpr = table.rows[0]._tr.get_or_add_trPr()
                    repeat = OxmlElement("w:tblHeader")
                    repeat.set(qn("w:val"), "true")
                    trpr.append(repeat)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
    path = OUT / "Estudo_Requisitos_Gestao_de_Demandas.docx"
    doc.save(path)
    return path


def build_pdf(blocks):
    pdfmetrics.registerFont(TTFont("Figtree", str(ASSETS / "figtree.ttf")))
    pdfmetrics.registerFont(TTFont("Figtree-Bold", str(ASSETS / "figtree-bold.ttf")))
    pdfmetrics.registerFont(TTFont("Lato", str(ASSETS / "lato.ttf")))
    pdfmetrics.registerFontFamily("Figtree", normal="Figtree", bold="Figtree-Bold", italic="Figtree", boldItalic="Figtree-Bold")
    page_w, page_h = A4
    doc = SimpleDocTemplate(str(OUT / "Estudo_Requisitos_Gestao_de_Demandas.pdf"), pagesize=A4,
        rightMargin=17*mm, leftMargin=17*mm, topMargin=21*mm, bottomMargin=17*mm,
        title="Estudo de requisitos da Gestão de Demandas", author="Gestão de Demandas")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyGD", fontName="Figtree", fontSize=8.7, leading=12.1, textColor=colors.HexColor("#14223A"), spaceAfter=6))
    styles.add(ParagraphStyle(name="H1GD", fontName="Figtree-Bold", fontSize=16, leading=20, textColor=colors.black, spaceBefore=12, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle(name="H2GD", fontName="Figtree-Bold", fontSize=11.4, leading=14.4, textColor=colors.black, spaceBefore=9, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name="H3GD", fontName="Figtree-Bold", fontSize=9.6, leading=12, textColor=colors.black, spaceBefore=7, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="BulletGD", parent=styles["BodyGD"], leftIndent=13, firstLineIndent=-8, spaceAfter=3))
    styles.add(ParagraphStyle(name="CellGD", fontName="Figtree", fontSize=6.8, leading=8.7, textColor=colors.HexColor("#14223A")))
    styles.add(ParagraphStyle(name="HeadCellGD", fontName="Figtree-Bold", fontSize=6.9, leading=8.7, textColor=colors.white))
    styles.add(ParagraphStyle(name="CoverTitleGD", fontName="Figtree-Bold", fontSize=28, leading=33, alignment=TA_LEFT, textColor=colors.black, spaceAfter=8))
    styles.add(ParagraphStyle(name="CoverSubGD", fontName="Lato", fontSize=13, leading=18, textColor=colors.HexColor("#52647C"), spaceAfter=16))
    flow = []
    if LOGO.exists():
        flow += [Spacer(1, 31*mm), PDFImage(str(LOGO), width=42*mm, height=28*mm, kind="proportional"), Spacer(1, 18*mm)]
    flow += [
        Paragraph("Estudo de requisitos<br/>Gestão de Demandas", styles["CoverTitleGD"]),
        Paragraph("Base de validação com o setor e especificação para o desenvolvimento definitivo", styles["CoverSubGD"]),
        Spacer(1, 8*mm),
        Paragraph("Versão 1.0 · 06 de novembro de 2026<br/>Protótipo funcional para descoberta e testes internos", styles["BodyGD"]),
        Spacer(1, 15*mm),
        Paragraph("Este documento descreve o retrato local do projeto e diferencia funções encontradas de decisões ainda sujeitas a validação. Alterações recentes de histórico, horas e relatórios permanecem locais e não devem ser presumidas na publicação atual.", styles["BodyGD"]),
        PageBreak()]
    started, avail = False, A4[0] - 34*mm
    for typ, value in blocks:
        if typ == "heading" and value[1].startswith("Estudo de requisitos da Gestão de Demandas"):
            continue
        if typ == "paragraph" and value.startswith("**Versão 1.0"):
            continue
        if typ == "heading" and value[1] == "1. Síntese executiva":
            started = True
        if not started:
            continue
        if typ == "heading":
            n, text = value
            sty = {1: styles["H1GD"], 2: styles["H2GD"], 3: styles["H3GD"]}[min(max(n, 1), 3)]
            flow.append(Paragraph(rich_reportlab(text), sty))
        elif typ == "paragraph":
            flow.append(Paragraph(rich_reportlab(value), styles["BodyGD"]))
        elif typ in ("bullet", "number"):
            for idx, item in enumerate(value, 1):
                prefix = "•" if typ == "bullet" else f"{idx}."
                flow.append(Paragraph(f"{prefix} &nbsp; {rich_reportlab(item)}", styles["BulletGD"]))
        elif typ == "table":
            rows, ncols = value, max(map(len, value))
            ratios = {2: [.23, .77], 3: [.18, .34, .48], 4: [.07, .43, .17, .33]}.get(ncols, [1/ncols]*ncols)
            data = []
            for ri, row in enumerate(rows):
                sty = styles["HeadCellGD"] if ri == 0 else styles["CellGD"]
                data.append([Paragraph(rich_reportlab(row[c] if c < len(row) else ""), sty) for c in range(ncols)])
            table = PDFTable(data, colWidths=[avail*x for x in ratios], repeatRows=1, splitByRow=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#005EB8")),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#D9D9D9")),
                ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
                ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F4F8FB")])]))
            flow += [table, Spacer(1,5)]

    def decorate(canvas, _doc):
        canvas.saveState()
        if _doc.page > 1:
            canvas.setStrokeColor(colors.HexColor("#DBDFE6"))
            canvas.line(17*mm, page_h-14*mm, page_w-17*mm, page_h-14*mm)
            canvas.setFont("Lato", 7.5)
            canvas.setFillColor(colors.HexColor("#52647C"))
            canvas.drawString(17*mm, page_h-11*mm, "GESTÃO DE DEMANDAS  |  ESTUDO DE REQUISITOS")
            canvas.drawRightString(page_w-17*mm, 9*mm, f"Versão 1.0  ·  06/11/2026     {_doc.page}")
        canvas.restoreState()
    doc.build(flow, onFirstPage=decorate, onLaterPages=decorate)
    return OUT / "Estudo_Requisitos_Gestao_de_Demandas.pdf"


def build_deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SlideInches(13.333), SlideInches(7.5)
    blank = prs.slide_layouts[6]
    def c(value): return SlideColor.from_string(value)
    def shape(slide, x,y,w,h,fill,rounded=False):
        sh=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,SlideInches(x),SlideInches(y),SlideInches(w),SlideInches(h))
        sh.fill.solid(); sh.fill.fore_color.rgb=c(fill); sh.line.fill.background()
        if rounded: sh.adjustments[0]=.04
        return sh
    def text(slide, value,x,y,w,h,size=18,fill=INK,bold=False,align=PP_ALIGN.LEFT):
        box=slide.shapes.add_textbox(SlideInches(x),SlideInches(y),SlideInches(w),SlideInches(h))
        tf=box.text_frame; tf.clear(); tf.word_wrap=True
        tf.margin_left=tf.margin_right=SlideInches(.05); tf.margin_top=tf.margin_bottom=SlideInches(.03)
        for i,line in enumerate(value.split("\n")):
            p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.text=line; p.alignment=align; p.space_after=SlidePt(4)
            for r in p.runs:
                r.font.name="Figtree"; r.font.size=SlidePt(size); r.font.bold=bold; r.font.color.rgb=c(fill)
        return box
    def table(slide,rows,x,y,w,h,widths,fs=14):
        t=slide.shapes.add_table(len(rows),len(rows[0]),SlideInches(x),SlideInches(y),SlideInches(w),SlideInches(h)).table
        for i,r in enumerate(widths): t.columns[i].width=SlideInches(w*r)
        for ri,row in enumerate(rows):
            for ci,val in enumerate(row):
                cell=t.cell(ri,ci); cell.text=str(val); cell.margin_left=cell.margin_right=SlideInches(.1); cell.margin_top=cell.margin_bottom=SlideInches(.055); cell.vertical_anchor=MSO_ANCHOR.MIDDLE
                cell.fill.solid(); cell.fill.fore_color.rgb=c(BLUE if ri==0 else (WHITE if ri%2 else PALE))
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.name="Figtree"; r.font.size=SlidePt(fs); r.font.bold=ri==0; r.font.color.rgb=c(WHITE if ri==0 else INK)
    def slide(title,kicker="ESTUDO DE REQUISITOS"):
        s=prs.slides.add_slide(blank); s.background.fill.solid(); s.background.fill.fore_color.rgb=c(WHITE)
        shape(s,0,0,13.333,.16,BLUE); text(s,kicker.upper(),.55,.36,12,.25,9,BLUE,True)
        text(s,title,.55,.73,12.2,.52,28,INK,True)
        text(s,"Gestão de Demandas  |  Base de validação  |  06.11.2026",.55,7.13,12.1,.20,8,MUTED)
        return s
    def bullets(s,items,x=.72,y=1.7,w=11.9,gap=.54,size=18):
        for i,item in enumerate(items):
            yy=y+i*gap; shape(s,x,yy+.16,.10,.10,BLUE); text(s,item,x+.25,yy,w-.25,gap-.04,size,INK)

    s=prs.slides.add_slide(blank); s.background.fill.solid(); s.background.fill.fore_color.rgb=c(WHITE); shape(s,0,0,13.333,1.2,BLUE)
    if LOGO.exists(): s.shapes.add_picture(str(LOGO),SlideInches(.7),SlideInches(.2),width=SlideInches(1.15))
    text(s,"PLANEJAR A SOLUÇÃO DEFINITIVA",2.1,.44,9.9,.28,12,WHITE,True)
    text(s,"Estudo de requisitos\nGestão de Demandas",.72,2,8.2,1.6,34,INK,True)
    text(s,"Retrato do protótipo, regras do negócio e decisões para homologação",.76,3.8,7.5,.85,20,MUTED)
    text(s,"Versão 1.0  |  06 de novembro de 2026",.76,5.45,5.8,.34,13,BLUE,True)
    text(s,"Dados de teste fictícios. Esta apresentação descreve a base local de trabalho.",.76,6.75,11.7,.28,10,MUTED)

    s=slide("O papel da plataforma nesta fase","CONTEXTO")
    text(s,"Um protótipo funcional para testar o processo antes de contratar a implementação institucional.",.75,1.7,11.5,.9,24,INK,True)
    table(s,[["Agora","Na validação","Na entrega oficial"],["Testar fluxos com dados fictícios","Confirmar regras e exceções com o setor","Implementar com arquitetura e operação aprovadas pela TI"],["Tornar decisões visíveis","Homologar custos, relatórios e permissões","Preservar integridade, acesso e histórico"]],.75,3,11.8,2.3,[.25,.37,.38],15)
    text(s,"O estudo descreve a versão local revisada em 06/11/2026. Melhorias recentes ainda não foram publicadas.",.8,5.75,11.6,.5,14,"C83B46")

    s=slide("A estrutura do estudo segue cinco perguntas","MÉTODO")
    table(s,[["O que?","Por quê?","Para quem?","Quando?","Como?"],["Demandas, cards e entregas","Compartilhar estado, critérios e histórico","Admin, gestor, equipe interna, fornecedor","Entrada, planejamento, execução e revisão","Navegador, regras no servidor e dados auditáveis"]],.62,2.15,12.1,2.7,[.16,.19,.20,.23,.22],16)
    text(s,"Adaptado do Pipeline de comunicação dos Produtos de Dados. As etapas de comunicação inspiram clareza e revisão, não viram funções do sistema.",.75,5.45,11.9,.6,13,MUTED)

    s=slide("O processo acompanha a demanda até a análise","ESCOPO")
    table(s,[["Planejar","Executar","Analisar"],["Backlog\nPrioridade\nCard individual\nSprint","Kanban\nCampos e anexos\nHoras\nRevisão e aprovação","Histórico\nDashboard\nRelatórios\nExcel, PDF e HTML"]],.75,1.85,11.8,2.8,[.33,.34,.33],17)
    text(s,"Fora da V1 confirmada: integrações corporativas, app móvel nativo, IA, apontamento diário e avaliação subjetiva de produtividade.",.85,5.25,11.5,.78,16,MUTED)

    s=slide("Perfis separados por papel e permissão","ACESSO")
    table(s,[["Perfil","Pode fazer","Não recebe automaticamente"],["Administrador","Configura usuários e permissões","Acesso irrestrito sem trilha de auditoria"],["Gestor","Opera demandas, fornecedor e sprint conforme concessão","Aprovar horas ou ver custos sem permissão"],["Usuário interno","Cria cards, organiza e exporta conforme concessão","Aprovação ou dados financeiros"],["Fornecedor","Vê suas tarefas e informa dados/horas","Tarefas alheias, custos, tarifas, relatórios"]],.6,1.72,12.1,4.75,[.21,.44,.35],14)

    s=slide("O fluxo Kanban tem validação em cada etapa","OPERAÇÃO")
    steps=["Backlog","A fazer","Em produção","Em revisão","Concluído"]
    x0,y0,bw,gap=.55,1.88,2.35,.18
    for i,label in enumerate(steps):
        x=x0+i*(bw+gap); shape(s,x,y0,bw,.72,BLUE if i<4 else "1E8549",True); text(s,label,x+.08,y0+.18,bw-.16,.32,17,WHITE,True,PP_ALIGN.CENTER)
    bullets(s,["Horas previstas não são obrigatórias por padrão. O criador configura o campo por card.","Transição inválida mantém o card na origem e explica o que precisa ser preenchido.","Fornecedor responsável executa; gestor autorizado aprova e conclui."],y=3.2,gap=.8,size=17)
    s.shapes.add_picture(str(MEDIA/"kanban.png"),SlideInches(9.25),SlideInches(4.15),height=SlideInches(2.45))
    text(s,"Captura do protótipo com dados fictícios.",9.25,6.63,3.3,.2,9,MUTED)

    s=slide("Cada card pode ter campos próprios","CONFIGURAÇÃO")
    bullets(s,["Tipos de campo e opções são definidos por atividade, com ordem, visibilidade e permissão de edição.","Obrigatoriedades adicionais podem ser associadas a uma transição.","A estimativa prevista pode estar ausente, opcional ou obrigatória. Horas utilizadas seguem regra nativa.","Alterar o schema cria nova versão e preserva valores já preenchidos."],x=.72,y=1.75,w=6.3,gap=1.02,size=15)
    s.shapes.add_picture(str(MEDIA/"hours-alert.png"),SlideInches(7.4),SlideInches(2),width=SlideInches(5.25))
    text(s,"Exemplo do aviso de transição por horas previstas.",7.45,5.12,5.1,.35,11,MUTED)

    s=slide("Horas aprovadas usam a tarifa congelada","REGRA FINANCEIRA")
    text(s,"Custo consolidado",.8,1.7,4,.48,25,BLUE,True)
    text(s,"horas utilizadas aprovadas × tarifa da alocação",.8,2.25,11.8,.7,29,INK,True)
    table(s,[["Tarifa na alocação","Nova tarifa depois","Apontamento aprovado","Custo preservado"],["R$ 120,00/h","R$ 150,00/h","8 horas","R$ 960,00"]],.78,3.6,11.8,1.55,[.25,.25,.25,.25],16)
    text(s,"Horas previstas orientam planejamento e não entram no custo. Rejeição, pendência ou reabertura tiram a versão do consolidado atual até nova aprovação.",.82,5.65,11.7,.68,15,MUTED)

    s=slide("A sprint conserva o histórico ao fechar","SCRUM")
    table(s,[["Planejada","Ativa","Encerrada"],["Nome, objetivo, período e responsável. Cards elegíveis entram no compromisso.","Execução no Kanban; entradas registradas; alterações respeitam concorrência.","Snapshot, autoria e data/hora. Pendentes voltam ao backlog; concluídos mantêm vínculo histórico."]],.75,1.92,11.8,2.65,[.31,.31,.38],16)
    text(s,"Reabertura exige permissão e justificativa. Ela não recupera cards que já foram replanejados em outra sprint.",.82,5.3,11.5,.65,15,MUTED)

    s=slide("Os relatórios medem o fluxo com definições explícitas","ANÁLISE")
    bullets(s,["Cards: idade, etapa, permanência por fase, passagens, reaberturas, lead time e ciclo.","Sprints: compromisso, concluídos, pendentes, devolvidos, taxa e evolução.","Backlog: volume, prioridade, idade, entradas, saídas e itens parados.","Campos do card viram filtros, exceto descrição. Condições combinam por E.","HTML, PDF e Excel usam o recorte autorizado; fornecedores não emitem relatórios."],x=.62,y=1.72,w=6.8,gap=.9,size=14)
    preview=ROOT/"artifacts"/"report-farol"/"panorama-preview.png"
    if preview.exists():
        s.shapes.add_picture(str(preview),SlideInches(7.7),SlideInches(1.8),width=SlideInches(5))
        text(s,"Prévia local com dados fictícios. Tempos corridos não são horas trabalhadas.",7.72,6.1,5,.45,10,MUTED)

    s=slide("Histórico registra ação, autoria e momento","AUDITORIA")
    table(s,[["Evento","Evidência esperada"],["Horas","Versão, valor anterior e novo, fornecedor, instante e estado da aprovação"],["Card e campos","Antes/depois do que mudou, configuração e valor que permaneceu"],["Fluxo e sprint","Movimento, reabertura, entrada/saída, fechamento e responsável"],["Aprovação","Decisão, justificativa, versão avaliada e autor"],["Colaboração","Comentário e metadados/hash do anexo"]],.72,1.65,11.85,4.9,[.22,.78],14)
    text(s,"O histórico do protótipo é persistente, mas ainda não é uma cadeia criptográfica inviolável nem armazenamento independente.",.8,6.55,11.5,.34,11,"C83B46")

    s=slide("A arquitetura oficial depende de decisão da TI","TECNOLOGIA")
    table(s,[["Camada","Base encontrada","Aprovação pendente"],["Interface","React, TypeScript, Vite","Navegadores e identidade visual institucional"],["API e regras","FastAPI, serviços, autorização no servidor","Integrações, identidade e política de segurança"],["Persistência","SQLAlchemy, Alembic, SQLite local","SGBD corporativo e estratégia de migração"],["Publicação","Vercel + Render Free para testes","Hospedagem, backup, disponibilidade e monitoramento"]],.7,1.75,11.9,3.55,[.2,.36,.44],14)
    text(s,"SQLite e Render Free são adequados a testes descartáveis. A documentação não recomenda essa configuração para operação institucional multiusuário.",.8,5.75,11.6,.7,15,"C83B46")

    s=slide("Homologação deve fechar regras de operação e custo","VALIDAÇÃO")
    table(s,[["Setor","Área financeira","TI"],["Campos mínimos, prioridades, fluxo, entradas/saídas, uso das sprints","Correção aprovada, competência, arredondamento, recorte e níveis de acesso","Banco, identidade, retenção, backups, recuperação, segurança e capacidade"]],.72,1.85,11.9,2.8,[.33,.33,.34],15)
    text(s,"Executar os cenários de aceite com perfis diferentes e somente dados fictícios. Registrar exceções, responsável pela decisão e data de aprovação.",.8,5.42,11.7,.7,16,INK,True)

    s=slide("O pacote para o desenvolvedor deve incluir evidências","ENTREGA")
    bullets(s,["Requisitos funcionais, regras de negócio, modelo de dados e permissões rastreáveis.","Fluxos aprovados pelo setor e critérios de aceite executáveis.","Decisões da TI sobre identidade, banco, hospedagem, segurança, retenção e recuperação.","Plano de testes automatizados, migrações, monitoramento, suporte e treinamento.","Registro formal de qualquer alteração de escopo ou regra deste estudo."],y=1.82,gap=.92,size=17)
    text(s,"Referências: Pipeline de comunicação dos Produtos de Dados; Design System Sebrae-CE; Farol Estratégico 3.0; código e documentação local do protótipo.",.78,6.35,11.8,.42,10,MUTED)

    out=OUT/"Apresentacao_Estudo_Requisitos_Gestao_de_Demandas.pptx"
    prs.save(out)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    blocks=parse_blocks(SOURCE.read_text(encoding="utf-8-sig"))
    for path in (build_docx(blocks),build_pdf(blocks),build_deck()):
        print(path, path.stat().st_size)
    print("blocks",len(blocks))

if __name__=="__main__":
    main()
