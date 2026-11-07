"""Generate a static, 16:9 PDF companion for the interactive requirements deck."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "estudo-requisitos" / "Apresentacao_Gestao_de_Demandas.pdf"
W, H = 960, 540

NAVY = colors.HexColor("#053665")
BLUE = colors.HexColor("#2A4FDA")
BLUE_DARK = colors.HexColor("#005EB8")
INK = colors.HexColor("#17223C")
MUTED = colors.HexColor("#53627C")
CANVAS = colors.HexColor("#F2F5FA")
LINE = colors.HexColor("#D9E0EA")
CYAN = colors.HexColor("#0B89A8")
CYAN_SOFT = colors.HexColor("#E5F5F8")
BLUE_SOFT = colors.HexColor("#EEF1FF")
GREEN = colors.HexColor("#267547")
GREEN_SOFT = colors.HexColor("#EAF6EF")
ORANGE = colors.HexColor("#915600")
ORANGE_SOFT = colors.HexColor("#FFF4DD")
RED = colors.HexColor("#A92D2D")
RED_SOFT = colors.HexColor("#FCEDEE")
PURPLE = colors.HexColor("#6342A1")
PURPLE_SOFT = colors.HexColor("#F1EDFA")
WHITE = colors.white

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
font_path = ROOT / "backend" / "app" / "report_assets" / "figtree-bold.ttf"
if font_path.exists():
    try:
        pdfmetrics.registerFont(TTFont("FigtreeBold", str(font_path)))
        FONT_BOLD = "FigtreeBold"
    except Exception:
        pass


def wrap(c: canvas.Canvas, text: str, x: float, y: float, width: float,
         size: float = 13, leading: float | None = None, color=INK,
         font: str = FONT, max_lines: int | None = None) -> float:
    """Draw wrapped text and return the y coordinate below it."""
    leading = leading or size * 1.36
    lines = simpleSplit(text, font, size, width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    c.setFillColor(color)
    c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def card(c: canvas.Canvas, x: float, top: float, width: float, height: float,
         title: str, body: str, tint=BLUE, tag: str | None = None,
         title_size: float = 16, body_size: float = 11.5) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.roundRect(x, top - height, width, height, 12, fill=1, stroke=1)
    c.setFillColor(tint)
    c.roundRect(x, top - height, 5, height, 3, fill=1, stroke=0)
    tx = x + 17
    ty = top - 23
    if tag:
        c.setFillColor(tint)
        c.setFont(FONT_BOLD, 8.5)
        c.drawString(tx, ty, tag.upper())
        ty -= 20
    ty = wrap(c, title, tx, ty, width - 32, title_size, title_size * 1.18,
              INK, FONT_BOLD, max_lines=2)
    ty -= 6
    wrap(c, body, tx, ty, width - 32, body_size, body_size * 1.35,
         MUTED, FONT, max_lines=max(2, int((height - (top - ty) - 16) / (body_size * 1.35))))


def grid_cards(c: canvas.Canvas, cards: list[tuple[str, str, str | None]],
               x: float = 44, top: float = 378, width: float = 872,
               height: float = 135, columns: int | None = None,
               gap: float = 13) -> None:
    if not cards:
        return
    columns = columns or min(3, len(cards))
    rows = (len(cards) + columns - 1) // columns
    card_h = (height - (rows - 1) * gap) / rows
    card_w = (width - (columns - 1) * gap) / columns
    for i, (title, body, tint_name) in enumerate(cards):
        row, col = divmod(i, columns)
        tint = {
            "blue": BLUE, "cyan": CYAN, "green": GREEN, "orange": ORANGE,
            "red": RED, "purple": PURPLE,
        }.get(tint_name or "blue", BLUE)
        card(c, x + col * (card_w + gap), top - row * (card_h + gap),
             card_w, card_h, title, body, tint=tint,
             title_size=15 if columns <= 3 else 12.5,
             body_size=10.4 if columns >= 4 else 11)


def chrome(c: canvas.Canvas, n: int, label: str, title: str, lead: str) -> float:
    c.setFillColor(CANVAS)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H - 9, W, 9, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.circle(W - 5, H - 5, 112, fill=1, stroke=0)
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.16))
    c.circle(W - 24, H - 3, 73, fill=1, stroke=0)
    c.setFillColor(BLUE_DARK)
    c.setFont(FONT_BOLD, 8.5)
    c.drawString(44, 489, label.upper())
    wrap(c, title, 44, 458, 825, 26, 29, BLUE_DARK, FONT_BOLD, max_lines=2)
    y = 398
    if lead:
        y = wrap(c, lead, 44, 397, 825, 12.5, 16.5, MUTED, FONT, max_lines=2) - 9
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(44, 36, 916, 36)
    c.setFillColor(MUTED)
    c.setFont(FONT, 8.5)
    c.drawString(44, 21, "GESTÃO DE DEMANDAS  ·  REQUISITOS PARA VALIDAÇÃO  ·  NOVEMBRO 2026")
    c.setFillColor(BLUE_DARK)
    c.setFont(FONT_BOLD, 9)
    c.drawRightString(916, 21, f"{n:02d}  /  15")
    return y


def note(c: canvas.Canvas, text: str, x=44, y=112, width=872,
         fill=ORANGE_SOFT, ink=ORANGE, label="VALIDAÇÃO") -> None:
    c.setFillColor(fill)
    c.roundRect(x, y, width, 52, 10, fill=1, stroke=0)
    c.setFillColor(ink)
    c.setFont(FONT_BOLD, 8)
    c.drawString(x + 15, y + 34, label)
    wrap(c, text, x + 15, y + 19, width - 30, 10.5, 13, INK, FONT, max_lines=2)


def cover(c: canvas.Canvas) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#075BA4"))
    c.circle(840, 235, 375, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0D7AA8"))
    c.circle(904, 200, 257, fill=1, stroke=0)
    c.setStrokeColor(colors.Color(1, 1, 1, alpha=.22))
    c.setLineWidth(1)
    c.circle(794, 259, 205, fill=0, stroke=1)
    c.circle(794, 259, 157, fill=0, stroke=1)
    c.circle(794, 259, 108, fill=0, stroke=1)
    logo = ROOT / "backend" / "app" / "report_assets" / "sebrae-cor.png"
    if logo.exists():
        c.setFillColor(WHITE)
        c.roundRect(44, 437, 91, 62, 12, fill=1, stroke=0)
        c.drawImage(ImageReader(str(logo)), 56, 444, width=67, height=48,
                    preserveAspectRatio=True, anchor="c", mask="auto")
    c.setFillColor(colors.Color(1, 1, 1, alpha=.82))
    c.setFont(FONT_BOLD, 9)
    c.drawString(153, 465, "ESTUDO PARA VALIDAÇÃO")
    c.setFillColor(colors.HexColor("#B8F1F8"))
    c.setFont(FONT_BOLD, 9)
    c.drawString(44, 382, "DA DESCOBERTA À ESPECIFICAÇÃO")
    wrap(c, "Gestão de Demandas", 44, 342, 620, 47, 52, WHITE, FONT_BOLD, max_lines=2)
    wrap(c, "Uma base comum para testar o processo com o setor e entregar ao desenvolvedor uma solução definida.",
         44, 225, 570, 19, 27, colors.HexColor("#EAF1FB"), FONT, max_lines=3)
    chips = ["REQUISITOS E REGRAS", "FLUXOS E PERMISSÕES", "INDICADORES E ACEITE", "VERSÃO 1.0 · 06 NOV 2026"]
    x = 44
    for chip in chips:
        tw = pdfmetrics.stringWidth(chip, FONT_BOLD, 8) + 22
        c.setFillColor(colors.Color(1, 1, 1, alpha=.12))
        c.roundRect(x, 107, tw, 26, 13, fill=1, stroke=0)
        c.setStrokeColor(colors.Color(1, 1, 1, alpha=.38))
        c.roundRect(x, 107, tw, 26, 13, fill=0, stroke=1)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 8)
        c.drawString(x + 11, 116, chip)
        x += tw + 8
    c.setFillColor(colors.HexColor("#FFD98A"))
    c.setFont(FONT_BOLD, 9)
    c.drawString(44, 72, "PROTÓTIPO DE TESTES · NÃO HOMOLOGADO PARA USO INSTITUCIONAL")
    app = "https://os-manager-phi.vercel.app"
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 9)
    c.drawString(44, 49, "Aplicação de teste: os-manager-phi.vercel.app")
    c.linkURL(app, (42, 43, 340, 64), relative=0, thickness=0)
    c.setFillColor(colors.Color(1, 1, 1, alpha=.7))
    c.setFont(FONT, 8)
    c.drawRightString(916, 22, "01 / 15")


def draw_flow(c: canvas.Canvas, names: list[tuple[str, str]], y=350,
              x=44, width=872, height=112) -> None:
    gap = 10
    w = (width - (len(names) - 1) * gap) / len(names)
    fills = [BLUE_SOFT, BLUE_SOFT, CYAN_SOFT, ORANGE_SOFT, GREEN_SOFT]
    colors_by = [BLUE, BLUE, CYAN, ORANGE, GREEN]
    for i, (title, subtitle) in enumerate(names):
        xx = x + i * (w + gap)
        c.setFillColor(fills[min(i, 4)])
        c.roundRect(xx, y - height, w, height, 12, fill=1, stroke=0)
        c.setFillColor(colors_by[min(i, 4)])
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(xx + w / 2, y - 25, f"ETAPA {i + 1}")
        title_lines = simpleSplit(title, FONT_BOLD, 13 if len(names) < 5 else 11.5, w - 18)
        ty = y - 49
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 13 if len(names) < 5 else 11.5)
        for line in title_lines[:2]:
            c.drawCentredString(xx + w / 2, ty, line)
            ty -= 15
        sub_lines = simpleSplit(subtitle, FONT, 9.2, w - 18)
        ty -= 2
        c.setFillColor(MUTED)
        c.setFont(FONT, 9.2)
        for line in sub_lines[:2]:
            c.drawCentredString(xx + w / 2, ty, line)
            ty -= 12
        if i < len(names) - 1:
            ax = xx + w + 2
            c.setStrokeColor(BLUE)
            c.setLineWidth(1.7)
            c.line(ax, y - height / 2, ax + gap - 4, y - height / 2)
            c.line(ax + gap - 8, y - height / 2 + 4, ax + gap - 4, y - height / 2)
            c.line(ax + gap - 8, y - height / 2 - 4, ax + gap - 4, y - height / 2)


def make_pdf() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(W, H), pageCompression=1)
    c.setTitle("Apresentação · Estudo de requisitos da Gestão de Demandas")
    c.setAuthor("Gestão de Demandas")
    c.setSubject("Resumo executivo para validação de requisitos com o setor")

    # 01 · Capa
    cover(c)
    c.showPage()

    # 02 · Propósito
    y = chrome(c, 2, "01 · Propósito", "O protótipo organiza a conversa antes da construção oficial",
               "A equipe experimenta regras e fluxos reais; o desenvolvedor recebe decisões validadas, não suposições.")
    grid_cards(c, [
        ("Testar com o setor", "Validar como demandas entram, avançam, voltam e são concluídas.", "blue"),
        ("Descobrir exceções", "Identificar lacunas em permissões, horas, aprovações, histórico e relatórios.", "cyan"),
        ("Especificar a V1", "Transformar acordos em requisitos verificáveis e critérios de aceite.", "green"),
    ], top=375, height=158)
    note(c, "O ambiente publicado é de demonstração. Dados, anexos e sessões podem desaparecer; use somente dados fictícios.", y=133)
    c.showPage()

    # 03 · Método
    chrome(c, 3, "02 · Método de levantamento", "Cinco perguntas conduzem o estudo",
           "A referência do Pipeline ajuda a sair da ideia e chegar a um produto compreensível, útil e validável.")
    grid_cards(c, [
        ("Produto", "O que: que problema operacional a plataforma resolve?", "blue"),
        ("Valor", "Por quê: que melhoria será percebida pelo setor?", "cyan"),
        ("Pessoas", "Para quem: quem cria, executa, aprova e acompanha?", "green"),
        ("Jornada", "Quando: em que momento cada decisão acontece?", "orange"),
        ("Operação", "Como: regras, dados e tecnologia sustentam o fluxo?", "purple"),
    ], top=365, height=228, columns=5, gap=9)
    note(c, "O estudo combina método, retrato do código local e decisões já tomadas; pontos pendentes permanecem explícitos.", y=94)
    c.showPage()

    # 04 · Escopo
    chrome(c, 4, "03 · Produto e escopo", "Um fluxo compartilhado entre demanda, execução e análise",
           "Backlog, cards, sprints, fornecedores, horas, aprovações e relatórios fazem parte da mesma trilha de trabalho.")
    grid_cards(c, [
        ("Planejar", "Backlog, prioridade e seleção de trabalho para sprint.", "blue"),
        ("Executar", "Kanban com regras de transição validadas pelo servidor.", "cyan"),
        ("Coordenar", "Fornecedores, horas e decisões de aprovação versionadas.", "green"),
        ("Aprender", "Histórico, tempo por fase, sprint e backlog.", "purple"),
    ], top=375, height=210, columns=2, gap=14)
    note(c, "Fora da V1: integrações externas, IA e aplicativos móveis. O sistema oficial depende de validação da equipe e da TI.", y=92)
    c.showPage()

    # 05 · Perfis
    chrome(c, 5, "04 · Pessoas e permissões", "O perfil indica o contexto; a permissão libera cada ação",
           "Toda autorização acontece no servidor, inclusive em consulta direta, filtros e arquivos exportados.")
    grid_cards(c, [
        ("Administrador", "Gerencia contas e concessões; acesso privilegiado é restrito e auditado.", "blue"),
        ("Gestor", "Organiza trabalho; aprova horas e vê custos somente com concessões específicas.", "cyan"),
        ("Interno autorizado", "Executa somente as ações liberadas para sua conta.", "purple"),
        ("Fornecedor", "Vê atividades atribuídas e informa horas; não acessa custos ou relatórios.", "orange"),
    ], top=375, height=210, columns=2, gap=14)
    note(c, "approve_hours, view_financial e export_financial são permissões distintas. Ser gestor não as concede automaticamente.", y=92, fill=BLUE_SOFT, ink=BLUE)
    c.showPage()

    # 06 · Fluxo
    chrome(c, 6, "05 · Kanban e ciclo de vida", "Uma sequência explícita protege o fluxo de trabalho",
           "O servidor valida ator, permissão, campos requeridos e versão antes de persistir um movimento.")
    draw_flow(c, [
        ("Backlog", "priorizar e preparar"), ("A fazer", "disponível para execução"),
        ("Em produção", "estimativa conforme card"), ("Em revisão", "horas e decisão"),
        ("Concluído", "gestor autorizado"),
    ], y=354, height=122)
    grid_cards(c, [
        ("Origem preservada", "Movimento recusado não altera etapa nem ordem.", "red"),
        ("Aviso objetivo", "Mensagem indica o dado que falta.", "orange"),
        ("Alternativa acessível", "Teclado e menu complementam o arrastar.", "cyan"),
    ], top=202, height=105)
    note(c, "Horas previstas são opcionais por padrão e configuráveis por card. Quando exigidas, precisam ser positivas antes da produção.", y=45)
    c.showPage()

    # 07 · Cards
    chrome(c, 7, "06 · Configuração individual", "Cada card pode ter seus próprios campos e regras",
           "O construtor visual prepara os dados da atividade sem substituir as estruturas que garantem o processo.")
    grid_cards(c, [
        ("Campos adicionais", "Texto, número, data, seleção, usuário, anexo e outros tipos seguros.", "blue"),
        ("Regras por etapa", "Obrigatoriedade posterior não impede salvar o card no início.", "cyan"),
        ("Estrutura nativa", "Status, sprint, fornecedor, horas, aprovação e tarifa têm campos próprios.", "green"),
        ("Schema versionado", "Mudanças de configuração não removem silenciosamente valores anteriores.", "purple"),
    ], top=375, height=205, columns=2, gap=14)
    note(c, "Horas previstas podem ser omitidas ou marcadas como obrigatórias por quem monta o card; campos livres não substituem horas estruturadas.", y=92)
    c.showPage()

    # 08 · Fornecedores
    chrome(c, 8, "07 · Fornecedores e tarifas", "Tarifas versionadas mantêm os custos históricos consistentes",
           "Na alocação, o sistema congela a tarifa então vigente. Reajustes futuros não reescrevem os vínculos anteriores.")
    grid_cards(c, [
        ("Cadastro", "Nome, função, ativo/inativo e vínculo de login quando necessário.", "blue"),
        ("Versão de tarifa", "Valor exato, vigência, autor e motivo opcional.", "cyan"),
        ("Alocação", "Card registra fornecedor, tarifa e snapshot congelado.", "purple"),
        ("Histórico íntegro", "Reajuste não altera alocação nem custo aprovado.", "green"),
    ], top=375, height=170, columns=4, gap=10)
    c.setFillColor(NAVY)
    c.roundRect(44, 93, 872, 99, 13, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#B8F1F8"))
    c.setFont(FONT_BOLD, 9)
    c.drawString(62, 165, "EXEMPLO FICTÍCIO · TARIFA CONGELADA")
    wrap(c, "8 horas aprovadas × R$ 120/h = R$ 960,00. Mesmo após reajuste para R$ 150/h, este custo histórico não muda.",
         62, 143, 820, 15, 20, WHITE, FONT_BOLD)
    c.showPage()

    # 09 · Horas
    chrome(c, 9, "08 · Horas, aprovação e custo", "Apontamento tem autoria, versão e decisão rastreáveis",
           "O fornecedor registra o total. Um gestor com permissão decide sobre aquela versão específica.")
    draw_flow(c, [
        ("Fornecedor", "preenche e salva"), ("Servidor", "registra nova versão"),
        ("Gestor", "aprova ou rejeita"), ("Custo", "consolida se aprovado"),
    ], y=350, height=100)
    grid_cards(c, [
        ("Rejeitada", "Fica em revisão; fornecedor corrige e reenvia.", "orange"),
        ("Aprovada", "Gestor autorizado pode concluir a atividade.", "green"),
        ("Reaberta", "Histórico persiste; custo sai do consolidado corrente.", "red"),
    ], top=220, height=98)
    c.setFillColor(BLUE_SOFT)
    c.roundRect(44, 55, 872, 57, 12, fill=1, stroke=0)
    c.setFillColor(BLUE_DARK)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(480, 88, "CUSTO = HORAS APROVADAS × TARIFA CONGELADA NA ALOCAÇÃO")
    c.setFillColor(MUTED)
    c.setFont(FONT, 9)
    c.drawCentredString(480, 70, "Horas previstas servem ao planejamento; não entram no cálculo financeiro.")
    c.showPage()

    # 10 · Histórico
    chrome(c, 10, "09 · Histórico e auditoria", "A linha do tempo explica o que aconteceu",
           "Alterações de etapa, dados do card e horas registram ator, instante, ação e contexto suficiente para revisão.")
    grid_cards(c, [
        ("Card criado", "Quem criou e quais campos foram inicializados.", "blue"),
        ("Movimentação", "Etapa anterior, etapa nova e validações executadas.", "cyan"),
        ("Horas alteradas", "Autor, data/hora, versão e valores comparáveis.", "orange"),
        ("Decisão", "Gestor, versão aprovada ou motivo da rejeição.", "green"),
    ], top=365, height=190, columns=2, gap=13)
    note(c, "A versão local registra eventos de negócio, mas não é uma trilha criptográfica imutável. Homologar retenção, acesso e backup institucional.", y=91, fill=PURPLE_SOFT, ink=PURPLE, label="LIMITE")
    c.showPage()

    # 11 · Relatórios
    chrome(c, 11, "10 · Relatórios e análises", "O histórico vira indicadores para investigar o trabalho",
           "Filtros usam campos do card, exceto descrição, e respeitam perfil, escopo e permissões de exportação.")
    grid_cards(c, [
        ("Card", "Tempo em cada fase, idade, ciclos, reaberturas e aprovações.", "blue"),
        ("Sprint", "Planejadas, concluídas, pendentes, devoluções e evolução.", "cyan"),
        ("Backlog", "Volume, prioridade, idade, entradas, saídas e prontidão.", "purple"),
    ], top=375, height=168)
    grid_cards(c, [
        ("Filtros", "Campos visíveis combinam por E e validam tipo no servidor.", "green"),
        ("Exportação", "Excel, PDF e HTML aplicam o mesmo recorte e as permissões.", "orange"),
    ], top=193, height=83, columns=2, gap=14)
    note(c, "Duração por fase é tempo corrido, inclusive noites e fins de semana. Não equivale a horas trabalhadas.", y=49, fill=BLUE_SOFT, ink=BLUE)
    c.showPage()

    # 12 · Métricas
    chrome(c, 12, "11 · Definições de métricas", "Fórmulas transparentes evitam interpretações inventadas",
           "Os indicadores são operacionais. O sistema não atribui nota subjetiva de desempenho a pessoas.")
    rows = [
        ("Conclusão", "Concluídas / planejadas × 100", "Denominador zero: vazio."),
        ("Em atraso", "Pendentes com prazo vencido", "Sem prazo não significa atraso."),
        ("Desvio de horas", "Utilizadas - previstas", "Estimativa pode não existir."),
        ("Lead time", "Criação até primeira conclusão", "Não mede trabalho ativo."),
        ("Cycle time", "Produção até conclusão", "Reabertura inicia novo ciclo."),
        ("Pontualidade", "No prazo / concluídos com prazo", "Mostrar amostra e denominador."),
    ]
    x0, top, widths = 44, 377, [145, 350, 377]
    c.setFillColor(NAVY)
    c.roundRect(x0, top - 30, sum(widths), 30, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 8.5)
    labels = ["INDICADOR", "FÓRMULA", "CUIDADO DE LEITURA"]
    xx = x0 + 12
    for label, width in zip(labels, widths):
        c.drawString(xx, top - 19, label)
        xx += width
    y = top - 30
    for i, row in enumerate(rows):
        rh = 37
        c.setFillColor(WHITE if i % 2 == 0 else colors.HexColor("#F7F9FC"))
        c.rect(x0, y - rh, sum(widths), rh, fill=1, stroke=0)
        xx = x0 + 12
        for j, (text, width) in enumerate(zip(row, widths)):
            wrap(c, text, xx, y - 15, width - 21, 9.4, 12,
                 BLUE_DARK if j == 0 else MUTED, FONT_BOLD if j == 0 else FONT, max_lines=2)
            xx += width
        y -= rh
    note(c, "Sete dias sem atualização é apenas limiar indicativo para validar; não é meta institucional.", y=65, fill=ORANGE_SOFT, ink=ORANGE, label="PARÂMETRO A VALIDAR")
    c.showPage()

    # 13 · Aceite
    chrome(c, 13, "12 · Plano de validação", "A homologação percorre o fluxo de ponta a ponta",
           "Os casos de aceite verificam que os acordos viraram comportamento consistente para cada perfil.")
    grid_cards(c, [
        ("01 · Demanda", "Card individual, campos por transição, fornecedor e tarifa congelada.", "blue"),
        ("02 · Planejamento", "Backlog, elegibilidade, sprint e proteção contra duplicidade.", "cyan"),
        ("03 · Execução", "Transições, horas, rejeição, correção e nova versão.", "orange"),
        ("04 · Encerramento", "Aprovação, custo, conclusão, dashboard e exportação.", "green"),
    ], top=375, height=158, columns=4, gap=10)
    grid_cards(c, [
        ("Tentativas indevidas", "IDOR de fornecedor, tarifa, aprovação sem concessão e exportação financeira.", "red"),
        ("Integridade histórica", "Sprint encerrada, reajuste, reabertura, schema e aprovação repetida.", "purple"),
    ], top=204, height=83, columns=2, gap=14)
    note(c, "O estudo completo detalha 16 casos de aceitação (CA-01 a CA-16).", y=57, fill=BLUE_SOFT, ink=BLUE)
    c.showPage()

    # 14 · Decisões
    chrome(c, 14, "13 · Próximas decisões", "Validar agora reduz retrabalho na construção",
           "A especificação orienta a conversa com o setor e evita preencher lacunas de processo por suposição.")
    decisions = [
        ("Fluxo e retornos", "Etapas, exceções, reabertura e retorno de sprint."),
        ("Acessos", "Quem concede permissões, aprova horas e vê custos?"),
        ("Relatórios", "Quais campos, tempos, recortes e fórmulas serão oficiais?"),
        ("Ambiente", "TI define banco, identidade, hospedagem, backup e operação."),
        ("Regras financeiras", "Correções após aprovação, competência e troca de fornecedor."),
    ]
    y = 375
    for i, (title, body) in enumerate(decisions, 1):
        c.setFillColor(WHITE)
        c.setStrokeColor(LINE)
        c.roundRect(44, y - 48, 872, 43, 9, fill=1, stroke=1)
        c.setFillColor(BLUE_SOFT)
        c.circle(67, y - 26, 12, fill=1, stroke=0)
        c.setFillColor(BLUE_DARK)
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(67, y - 29, f"{i:02d}")
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 10)
        c.drawString(88, y - 23, title)
        c.setFillColor(MUTED)
        c.setFont(FONT, 9.4)
        c.drawString(275, y - 23, body)
        y -= 55
    note(c, "SQLite é temporário para protótipo e teste. A troca futura de SGBD exige avaliação, migração ensaiada, testes de integridade e plano de rollback.", y=49, fill=ORANGE_SOFT, ink=ORANGE, label="DECISÃO DA TI")
    c.showPage()

    # 15 · Encerramento
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#075BA4"))
    c.circle(900, 200, 325, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#B8F1F8"))
    c.setFont(FONT_BOLD, 9)
    c.drawString(52, 465, "MATERIAIS DE APOIO")
    wrap(c, "Da apresentação à especificação detalhada", 52, 421, 770, 34, 40, WHITE, FONT_BOLD, max_lines=2)
    wrap(c, "Use o relatório completo para acompanhar requisitos, regras e critérios de aceite durante a validação com o setor.",
         52, 334, 700, 16, 23, colors.HexColor("#EAF1FB"), FONT)
    card(c, 52, 268, 265, 106, "Estudo de requisitos", "Requisitos, regras de negócio, modelo de dados e critérios de aceite.", BLUE, body_size=10.2)
    card(c, 337, 268, 265, 106, "Apresentação", "Resumo executivo para conduzir a conversa com o setor.", CYAN, body_size=10.2)
    card(c, 622, 268, 286, 106, "Protótipo de testes", "Ambiente temporário; use somente cadastros e informações fictícias.", GREEN, body_size=10.2)
    c.setFillColor(WHITE)
    c.roundRect(52, 102, 345, 53, 12, fill=1, stroke=0)
    c.setFillColor(BLUE_DARK)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(224, 123, "ABRIR A APLICAÇÃO DE TESTE")
    c.linkURL("https://os-manager-phi.vercel.app", (52, 102, 397, 155), relative=0, thickness=0)
    wrap(c, "Retrato local de 06/11/2026. As alterações podem não estar publicadas. A versão definitiva depende de homologação do setor e avaliação da TI.",
         52, 75, 840, 9.3, 13, colors.HexColor("#D5E1F1"), FONT, max_lines=2)
    c.setFillColor(colors.Color(1, 1, 1, alpha=.7))
    c.setFont(FONT, 8.5)
    c.drawRightString(916, 22, "15 / 15")
    c.showPage()

    c.save()


if __name__ == "__main__":
    make_pdf()
    print(f"PDF criado: {OUT}")
