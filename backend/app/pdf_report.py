"""Paginated editorial PDF, inspired by the supplied Farol Estratégico layout."""

from io import BytesIO
from pathlib import Path
from decimal import Decimal
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    CondPageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Wedge
from .html_report import duration, number, stamp
from .report_layout import executive, event_label
from .report_filters import STATUSES, APPROVALS
from .settings import APP_TIMEZONE

ASSETS = Path(__file__).parent / "report_assets"
# Centralized print palette: brand, ink, feedback, surfaces and borders.
PALETTE = {
    "primary": "#2B4EDA",
    "heading": "#142D8F",
    "ink": "#14213D",
    "muted": "#5E6579",
    "line": "#DEE2EA",
    "surface": "#F4F6FA",
    "success": "#1E8549",
    "error": "#DB3024",
    "warning": "#F59F0A",
    "secondary": "#11A0D4",
    "neutral": "#5E6378",
    "white": "#FFFFFF",
}
C = {key: colors.HexColor(value) for key, value in PALETTE.items()}
WIDTH = landscape(A4)[0] - 56


def build_pdf(data, financial, filters):
    for name, file in [
        ("Figtree", "figtree.ttf"),
        ("FigtreeBold", "figtree-bold.ttf"),
        ("Lato", "lato.ttf"),
    ]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(ASSETS / file)))
    pdfmetrics.registerFontFamily(
        "Figtree", normal="Figtree", bold="FigtreeBold", italic="Figtree", boldItalic="FigtreeBold"
    )
    styles = {
        "body": ParagraphStyle(
            "body", fontName="Figtree", fontSize=8.5, leading=12, textColor=C["ink"]
        ),
        "small": ParagraphStyle(
            "small", fontName="Lato", fontSize=7.5, leading=10.5, textColor=C["muted"]
        ),
        "eyebrow": ParagraphStyle(
            "eyebrow",
            fontName="FigtreeBold",
            fontSize=8,
            leading=12,
            textColor=C["primary"],
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "title",
            fontName="FigtreeBold",
            fontSize=25,
            leading=29,
            textColor=C["heading"],
            spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="FigtreeBold", fontSize=16, leading=21, textColor=C["ink"], spaceAfter=8
        ),
        "h3": ParagraphStyle(
            "h3", fontName="FigtreeBold", fontSize=11, leading=15, textColor=C["ink"], spaceAfter=5
        ),
        "value": ParagraphStyle(
            "value", fontName="FigtreeBold", fontSize=16, leading=19, textColor=C["ink"]
        ),
    }

    def p(value, style="body"):
        return Paragraph(
            escape(str(value if value is not None else "Indisponível")).replace("\n", "<br/>"),
            styles[style],
        )

    def table(headers, rows, weights=None, caption=None):
        weights = weights or [1] * len(headers)
        widths = [WIDTH * value / sum(weights) for value in weights]
        empty = not rows
        rows = rows or [["Nenhum registro neste recorte."] + [""] * (len(headers) - 1)]
        contents = [[p(caption, "h3")] + [""] * (len(headers) - 1)] if caption else []
        header = len(contents)
        contents += [[p(h, "small") for h in headers]] + [[p(v) for v in row] for row in rows]
        result = Table(
            contents, colWidths=widths, repeatRows=header + 1, hAlign="LEFT", splitInRow=1
        )
        commands = [
            ("BACKGROUND", (0, header), (-1, header), C["surface"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, header), (-1, -1), 0.4, C["line"]),
            ("ROWBACKGROUNDS", (0, header + 1), (-1, -1), [C["white"], colors.HexColor("#FBFCFE")]),
        ]
        if caption:
            commands += [("SPAN", (0, 0), (-1, 0)), ("LEFTPADDING", (0, 0), (-1, 0), 0)]
        if empty:
            commands += [("SPAN", (0, header + 1), (-1, header + 1))]
        result.setStyle(TableStyle(commands))
        return [result, Spacer(1, 10)]

    def chapter(kicker, title, subtitle):
        return [p(kicker, "eyebrow"), p(title, "title"), p(subtitle, "small"), Spacer(1, 16)]

    def chart(title, subtitle, values, w=380, height=184):
        drawing = Drawing(w, height)
        drawing.add(
            Rect(
                0,
                0,
                w,
                height,
                rx=8,
                ry=8,
                fillColor=C["white"],
                strokeColor=C["line"],
                strokeWidth=0.6,
            )
        )
        drawing.add(
            String(14, height - 22, title, fontName="FigtreeBold", fontSize=11, fillColor=C["ink"])
        )
        drawing.add(
            String(14, height - 37, subtitle, fontName="Lato", fontSize=7.5, fillColor=C["muted"])
        )
        maximum = max((v for _, v, _ in values), default=0) or 1
        for i, (label, value, formatted) in enumerate(values):
            y = height - 55 - i * 24
            drawing.add(String(14, y, label, fontName="Figtree", fontSize=8, fillColor=C["muted"]))
            drawing.add(
                String(
                    w - 14,
                    y,
                    formatted,
                    fontName="FigtreeBold",
                    fontSize=8,
                    fillColor=C["ink"],
                    textAnchor="end",
                )
            )
            drawing.add(
                Rect(14, y - 12, w - 28, 5, rx=2, ry=2, fillColor=C["surface"], strokeColor=None)
            )
            drawing.add(
                Rect(
                    14,
                    y - 12,
                    (w - 28) * value / maximum,
                    5,
                    rx=2,
                    ry=2,
                    fillColor=C["primary"] if i % 2 == 0 else C["secondary"],
                    strokeColor=None,
                )
            )
        return drawing

    def donut(cards, w=380, height=184):
        drawing = Drawing(w, height)
        drawing.add(
            Rect(
                0,
                0,
                w,
                height,
                rx=8,
                ry=8,
                fillColor=C["white"],
                strokeColor=C["line"],
                strokeWidth=0.6,
            )
        )
        drawing.add(
            String(
                14,
                height - 22,
                "Distribuição da carteira",
                fontName="FigtreeBold",
                fontSize=11,
                fillColor=C["ink"],
            )
        )
        drawing.add(
            String(
                14,
                height - 37,
                "Quantidade de demandas por etapa",
                fontName="Lato",
                fontSize=7.5,
                fillColor=C["muted"],
            )
        )
        drawing.add(Circle(78, 75, 47, fillColor=C["surface"], strokeColor=None))
        palette = ["neutral", "secondary", "primary", "warning", "success"]
        start = 90
        for index, (status, label) in enumerate(STATUSES.items()):
            count = sum(c["status"] == status for c in cards)
            angle = 360 * count / len(cards) if cards else 0
            if angle:
                drawing.add(
                    Wedge(
                        78,
                        75,
                        47,
                        start - angle,
                        start,
                        fillColor=C[palette[index]],
                        strokeColor=None,
                    )
                )
            start -= angle
            y = 120 - index * 21
            drawing.add(Rect(158, y - 2, 6, 6, fillColor=C[palette[index]], strokeColor=None))
            drawing.add(String(172, y, label, fontName="Figtree", fontSize=8, fillColor=C["muted"]))
            drawing.add(
                String(
                    w - 18,
                    y,
                    str(count),
                    fontName="FigtreeBold",
                    fontSize=9,
                    fillColor=C["ink"],
                    textAnchor="end",
                )
            )
        drawing.add(Circle(78, 75, 35, fillColor=C["white"], strokeColor=None))
        drawing.add(
            String(
                78,
                76,
                str(len(cards)),
                fontName="FigtreeBold",
                fontSize=25,
                fillColor=C["ink"],
                textAnchor="middle",
            )
        )
        drawing.add(
            String(
                78,
                62,
                "cards",
                fontName="Lato",
                fontSize=8,
                fillColor=C["muted"],
                textAnchor="middle",
            )
        )
        return drawing

    def pair(left, right):
        t = Table([[left, right]], colWidths=[WIDTH / 2, WIDTH / 2], hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return t

    def page(canvas, doc):
        canvas.saveState()
        w, h = landscape(A4)
        canvas.drawImage(
            str(ASSETS / "sebrae-cor.png"),
            28,
            h - 45,
            width=52,
            height=35,
            mask="auto",
            preserveAspectRatio=True,
        )
        canvas.setFillColor(C["heading"])
        canvas.setFont("FigtreeBold", 10)
        canvas.drawString(95, h - 25, "Gestão de Demandas")
        canvas.setFillColor(C["muted"])
        canvas.setFont("Lato", 7.5)
        canvas.drawString(95, h - 37, "RELATÓRIO GERENCIAL · SEBRAE CEARÁ")
        canvas.drawRightString(w - 28, h - 26, stamp(data["as_of"]) + " · " + APP_TIMEZONE)
        canvas.setStrokeColor(C["line"])
        canvas.line(28, h - 52, w - 28, h - 52)
        canvas.line(28, 28, w - 28, 28)
        canvas.setFont("Lato", 7)
        canvas.drawString(
            28, 16, "Retrato estático · Escopo autorizado e filtrado · Compartilhamento restrito"
        )
        canvas.drawRightString(w - 28, 16, f"Gestão de Demandas / {doc.page:02d}")
        canvas.restoreState()

    reading = executive(data, financial)
    cards = data["items"]
    story = chapter(
        "01 / PANORAMA DA OPERAÇÃO",
        "Entregas em perspectiva",
        "Execução das demandas, pontos de atenção e evidências do fluxo.",
    )
    synth = []
    for title, body, tone in reading["synthesis"]:
        style = ParagraphStyle("synth-" + tone, parent=styles["eyebrow"], textColor=C[tone])
        synth.append([Paragraph(escape(title), style), p(body)])
    synthesis = Table([synth], colWidths=[WIDTH / 3] * 3)
    synthesis.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C["surface"]),
                ("BOX", (0, 0), (-1, -1), 0.5, C["line"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, C["line"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story += [synthesis, Spacer(1, 14)]
    cells = []
    for label, value, note, tone in reading["kpis"]:
        cells.append(
            [
                p(label.upper(), "small"),
                Spacer(1, 3),
                p(value, "value"),
                Spacer(1, 2),
                p(note, "small"),
            ]
        )
    kpis = Table([cells], colWidths=[WIDTH / 6] * 6)
    kpis.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), C["white"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, C["line"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, C["line"]),
            ]
            + [
                ("LINEABOVE", (index, 0), (index, 0), 2, C[tone])
                for index, (_, _, _, tone) in enumerate(reading["kpis"])
            ]
        )
    )
    story += [
        kpis,
        Spacer(1, 8),
        pair(
            donut(cards, height=158),
            chart(
                "Onde o trabalho permanece",
                "Tempo corrido comprovado; não equivale a esforço",
                [
                    (STATUSES[r["status"]], r["duration_seconds"], duration(r["duration_seconds"]))
                    for r in data["summary"]["phase_seconds"]
                ],
                height=158,
            ),
        ),
        Spacer(1, 6),
        p(
            f"Históricos completos: {data['summary']['complete_histories']} de {len(cards)}. Sem evidência, a duração fica indisponível. Cards sem prazo não são classificados em atraso.",
            "small",
        ),
    ]
    story += [PageBreak()] + chapter(
        "02 / GESTÃO DAS ENTREGAS",
        "Ritmo das sprints e saúde do backlog",
        "Compromisso, alterações de escopo e trabalho que permanece na fila.",
    )
    story += table(
        ["Sprint / estado", "Iniciais", "Concluídos", "Pendentes", "Adicionados", "Devolvidos"],
        [
            [
                s["name"]
                + " · "
                + {"planned": "Planejada", "active": "Ativa", "closed": "Encerrada"}.get(
                    s["state"], s["state"]
                ),
                s["initial_cards"],
                s["done"],
                s["pending"],
                s["added_after_start"],
                s["returned"],
            ]
            for s in data["sprints"]
        ],
        [3.3, 1, 1, 1, 1, 1],
        "Sprints no recorte",
    )
    backlog = data["summary"]["backlog"]
    story += table(
        ["No backlog", "Sem fornecedor", "Em atraso", "Sem alteração observada"],
        [
            [
                backlog["count"],
                backlog["unassigned"],
                backlog["overdue"],
                str(backlog["idle"]) + " · " + str(backlog["idle_days"]) + " dias ou mais",
            ]
        ],
    )
    story += table(
        ["Card", "Atividade", "Fornecedor", "Idade", "Na fase atual"],
        [
            [
                f"OS-{c['id']}",
                c["title"],
                c["supplier_name"] or "Não atribuído",
                duration(c["age_seconds"]),
                duration(c["current_phase_seconds"]),
            ]
            for c in data["backlog_oldest"]
        ],
        [0.7, 3, 1.5, 1, 1],
        "Mais antigos do backlog · até dez cards",
    )
    story += [
        p("Planejamento e realização", "h3"),
        chart(
            "Esforço registrado",
            "Horas previstas, utilizadas e aprovadas",
            [
                (label, minutes, number(Decimal(minutes) / 60) + "h")
                for label, minutes in reading["hours"]
            ],
            w=WIDTH,
            height=125,
        ),
    ]
    story += [PageBreak()] + chapter(
        "03 / CARTEIRA CONSOLIDADA",
        "Demandas do recorte",
        "Relação completa de cards; os detalhes individuais seguem nas próximas páginas.",
    )
    headers = ["ID", "Atividade", "Etapa", "Fornecedor", "Na fase atual", "Até 1ª conclusão"] + (
        ["Custo consolidado"] if financial else []
    )
    rows = [
        [
            f"OS-{c['id']}",
            c["title"],
            STATUSES[c["status"]],
            c["supplier_name"] or "Não atribuído",
            duration(c["current_phase_seconds"]),
            duration(c["lead_time_seconds"]),
        ]
        + (["R$ " + number(Decimal(c.get("cost_cents", 0) or 0) / 100)] if financial else [])
        for c in cards
    ]
    story += table(headers, rows, [0.65, 2.7, 1.1, 1.3, 1, 1] + ([1.1] if financial else []))
    story += [PageBreak()] + chapter(
        "04 / RASTREABILIDADE",
        "Históricos dos cards",
        "Passagens por etapa, apontamentos e decisões com suas respectivas evidências.",
    )
    for card in cards:
        story += [
            CondPageBreak(150),
            KeepTogether(
                [
                    p(f"OS-{card['id']} / {card['title']}", "h2"),
                    p(
                        STATUSES[card["status"]]
                        + " · "
                        + (card["supplier_name"] or "Sem fornecedor")
                        + " · Observado até "
                        + stamp(card["as_of"]),
                        "small",
                    ),
                    Spacer(1, 10),
                ]
            ),
        ]
        if not card["history_complete"]:
            story += [
                p("Histórico parcial: " + "; ".join(card["history_issues"]), "small"),
                Spacer(1, 8),
            ]
        story += table(
            [
                "Idade do registro",
                "Até 1ª conclusão",
                "Horas previstas",
                "Horas utilizadas",
                "Horas aprovadas",
            ],
            [
                [
                    duration(card["age_seconds"]),
                    duration(card["lead_time_seconds"]),
                    number(Decimal(card["estimated_minutes"]) / 60) + "h"
                    if card["estimated_minutes"]
                    else "Sem estimativa",
                    number(Decimal(card["used_minutes"]) / 60) + "h",
                    number(Decimal(card["approved_minutes"]) / 60) + "h",
                ]
            ],
        )
        story += table(
            ["Etapa", "Entrada", "Saída", "Permanência", "Evidência"],
            [
                [
                    STATUSES[v["status"]],
                    stamp(v["entered_at"]),
                    stamp(v["exited_at"]) if v["exited_at"] else "Em aberto",
                    duration(v["duration_seconds"]),
                    "Comprovada" if v["complete"] else "Parcial",
                ]
                for v in card["periods"]
            ],
            [1.2, 1.4, 1.4, 1, 1],
            f"OS-{card['id']} · Passagens por fase",
        )
        if card["approval_history"]:
            story += table(
                [
                    "Versão",
                    "Horas",
                    "Decisão",
                    "Enviado em",
                    "Decidido em",
                    "Espera",
                    "Justificativa",
                ],
                [
                    [
                        a["hours_version"],
                        number(Decimal(a["used_minutes"]) / 60),
                        APPROVALS[a["state"]],
                        stamp(a["submitted_at"]),
                        stamp(a["decision_at"]),
                        duration(a["waiting_seconds"]),
                        a["reason"],
                    ]
                    for a in card["approval_history"]
                ],
                [0.5, 0.6, 1, 1.2, 1.2, 0.8, 1.7],
                f"OS-{card['id']} · Apontamentos e aprovações",
            )
        else:
            story += [
                p(f"OS-{card['id']} · Apontamentos: nenhum envio registrado.", "small"),
                Spacer(1, 10),
            ]
        story += table(
            ["Instante", "Autor", "Evento / movimentação", "Justificativa"],
            [
                [
                    stamp(v["at"]),
                    v["actor"],
                    event_label(v["action"])
                    + (
                        " · "
                        + STATUSES.get(v["origin"], "")
                        + " → "
                        + STATUSES.get(v["destination"], "")
                        if v["origin"] or v["destination"]
                        else ""
                    ),
                    v["reason"],
                ]
                for v in card["timeline"]
            ],
            [1.2, 1, 2, 2],
            f"OS-{card['id']} · Linha do tempo",
        )
        visible = [
            [f["label"], str(card["values"][f["id"]])]
            for f in card["fields"]
            if f["id"] in card["values"]
        ]
        if visible:
            story += table(
                ["Campo adicional", "Valor"],
                visible,
                [1, 3],
                f"OS-{card['id']} · Campos visíveis preenchidos",
            )
        if financial:
            story += [
                p(
                    "Custo consolidado: R$ "
                    + number(Decimal(card.get("cost_cents", 0) or 0) / 100),
                    "h3",
                )
            ]
        story += [Spacer(1, 14)]
    story += [PageBreak()] + chapter(
        "05 / CRITÉRIOS DE LEITURA",
        "Escopo, filtros e metodologia",
        "Definições transparentes para interpretar os dados deste relatório.",
    )
    applied = [str(rule) for rule in data["filters"]]
    for key, label in [
        ("status", "Etapa"),
        ("sprint_id", "Sprint ID"),
        ("supplier_id", "Fornecedor ID"),
        ("starts", "Criados desde"),
        ("ends", "Criados até"),
        ("min_phase_hours", "Tempo mínimo na fase (h)"),
        ("overdue_only", "Somente atrasados"),
        ("only_reopened", "Somente reabertos"),
        ("approval_state", "Aprovação"),
    ]:
        if filters.get(key) not in (None, "", False):
            applied.append(
                label
                + ": "
                + (
                    stamp(str(filters[key]) + "T00:00:00").split(" ")[0]
                    if key in {"starts", "ends"}
                    else STATUSES.get(
                        str(filters[key]), APPROVALS.get(str(filters[key]), str(filters[key]))
                    )
                )
            )
    story += table(
        ["Filtro aplicado"],
        [[value] for value in applied] or [["Todos os dados do escopo autorizado"]],
    )
    for title, body in [
        ("Conclusão", "Cards concluídos ÷ cards no recorte × 100. Sem base, não há percentual."),
        (
            "Tempo e esforço",
            "Permanência usa tempo corrido. Não equivale a horas trabalhadas. Concluído é terminal; reaberturas preservam ciclos. Estimativas ausentes não entram no planejamento e horas não aprovadas não integram os totais consolidados.",
        ),
        ("Corte temporal", data["period_basis"]),
        ("Eventos no período", data["summary"]["recorded_flow"]["basis"]),
        (
            "Integridade e compartilhamento",
            "Registros sem evidência são sinalizados. Retrato estático, sem atualização automática. Compartilhe somente com pessoas autorizadas.",
        ),
    ]:
        story += [p(title, "h3"), p(body), Spacer(1, 14)]
    buffer = BytesIO()
    SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=28,
        rightMargin=28,
        topMargin=67,
        bottomMargin=42,
        title="Relatório gerencial · Gestão de Demandas",
        author="Gestão de Demandas",
        allowSplitting=True,
    ).build(story, onFirstPage=page, onLaterPages=page)
    buffer.seek(0)
    return buffer, "application/pdf"
