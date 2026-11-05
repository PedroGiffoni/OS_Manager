from io import BytesIO
from xml.sax.saxutils import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .report_filters import STATUSES, APPROVALS


def build_export(format, data, financial, filters):
    cards = data["items"]
    sheets = {}
    headings = [
        "ID",
        "Título",
        "Fornecedor",
        "Etapa",
        "Criado em UTC",
        "Observado até UTC",
        "Histórico completo",
        "Ressalvas",
        "Idade do registro (s)",
        "Etapa atual (s)",
        "Criação até primeira conclusão (s)",
        "Último ciclo (s)",
        "Prazo",
        "Situação prazo",
        "Dias atraso",
        "Previstas (min)",
        "Utilizadas (min)",
        "Aprovadas (min)",
        "Desvio (min)",
        "Reaberturas registradas",
        "Rejeições registradas",
        "Reapresentações",
        "Sprints visitadas",
    ]
    if financial:
        headings += ["Custo consolidado (centavos)", "Tarifa congelada (centavos/h)"]
    sheets["Cards"] = (
        headings,
        [
            [
                card["id"],
                card["title"],
                card["supplier_name"],
                STATUSES[card["status"]],
                card["created_at"],
                card["as_of"],
                card["history_complete"],
                "; ".join(card["history_issues"]),
                card["age_seconds"],
                card["current_phase_seconds"],
                card["lead_time_seconds"],
                card["cycles"][-1]["duration_seconds"] if card["cycles"] else None,
                card["due"],
                card["deadline"]["state"],
                card["deadline"]["late_days"],
                card["estimated_minutes"],
                card["used_minutes"],
                card["approved_minutes"],
                card["hours_deviation_minutes"],
                card["reopen_count"],
                card["rejection_count"],
                card["resubmission_count"],
                card["sprints_visited"],
            ]
            + ([card.get("cost_cents"), card.get("rate_cents")] if financial else [])
            for card in cards
        ],
    )
    sheets["Fases"] = (
        [
            "Card ID",
            "Etapa",
            "Entrada UTC",
            "Saída UTC",
            "Duração observada (s)",
            "Intervalo comprovado",
            "Passagem aberta",
            "Entrada por",
            "Saída por",
        ],
        [
            [
                card["id"],
                STATUSES[period["status"]],
                period["entered_at"],
                period["exited_at"],
                period["duration_seconds"],
                period["complete"],
                period["open"],
                period["entry_actor"],
                period["exit_actor"],
            ]
            for card in cards
            for period in card["periods"]
        ],
    )
    sheets["Linha do tempo"] = (
        ["Card ID", "Evento", "Instante UTC", "Autor", "Origem", "Destino", "Justificativa"],
        [
            [
                card["id"],
                event["action"],
                event["at"],
                event["actor"],
                STATUSES.get(event["origin"], ""),
                STATUSES.get(event["destination"], ""),
                event["reason"],
            ]
            for card in cards
            for event in card["timeline"]
        ],
    )
    sheets["Aprovações"] = (
        [
            "Card ID",
            "Versão horas",
            "Enviado UTC",
            "Fornecedor",
            "Utilizadas (min)",
            "Decisão",
            "Decidido UTC",
            "Autor decisão",
            "Espera observada (s)",
            "Motivo",
        ],
        [
            [
                card["id"],
                entry["hours_version"],
                entry["submitted_at"],
                entry["submitted_by"],
                entry["used_minutes"],
                APPROVALS[entry["state"]],
                entry["decision_at"],
                entry["decision_by"],
                entry["waiting_seconds"],
                entry["reason"],
            ]
            for card in cards
            for entry in card["approval_history"]
        ],
    )
    sheets["Sprints"] = (
        [
            "Sprint ID",
            "Nome",
            "Estado",
            "Observado até UTC",
            "Base inicial conhecida",
            "Cards iniciais",
            "Iniciais concluídos",
            "Cumprimento inicial (%)",
            "Adicionados após início",
            "Concluídos",
            "Pendentes",
            "Devolvidos",
            "Cards no recorte",
            "Previstas (min)",
            "Utilizadas (min)",
            "Aprovadas (min)",
            "Cards com estimativa",
        ]
        + (["Custo aprovado (centavos)"] if financial else []),
        [
            [
                sprint["id"],
                sprint["name"],
                sprint["state"],
                sprint["as_of"],
                sprint["history_complete"],
                sprint["initial_cards"],
                sprint["initial_done"],
                sprint["commitment_percent"],
                sprint["added_after_start"],
                sprint["done"],
                sprint["pending"],
                sprint["returned"],
                sprint["scope_cards"],
                sprint["estimated_minutes"],
                sprint["used_minutes"],
                sprint["approved_minutes"],
                sprint["estimated_cards"],
            ]
            + ([sprint.get("cost_cents")] if financial else [])
            for sprint in data["sprints"]
        ],
    )
    sheets["Backlog"] = (
        [
            "Card ID",
            "Título",
            "Prioridade",
            "Fornecedor",
            "Idade (s)",
            "Permanência atual (s)",
            "Sem alteração observada (s)",
            "Pendências visíveis para produção",
        ],
        [
            [
                card["id"],
                card["title"],
                card["priority"],
                card["supplier_name"],
                card["age_seconds"],
                card["current_phase_seconds"],
                card["idle_seconds"],
                "; ".join(card["production_missing_fields"]),
            ]
            for card in cards
            if card["status"] == "backlog"
        ],
    )
    notes = [
        "Tempos em segundos corridos; não representam horas trabalhadas ou faturáveis.",
        "Célula vazia em duração significa indisponível/não aplicável; zero pode representar intervalo comprovado menor que um segundo.",
        "Concluído é terminal e sua permanência não integra os tempos ativos.",
        "Criação até primeira conclusão exige histórico completo; reaberturas preservam ciclos separados.",
        "Resumos de sprint se referem ao recorte autorizado e filtrado.",
        data["period_basis"],
        data["summary"]["recorded_flow"]["basis"],
    ]
    buffer = BytesIO()
    if format == "xlsx":
        book = Workbook()
        book.remove(book.active)
        for name, (columns, values) in sheets.items():
            sheet = book.create_sheet(name)
            sheet.append(columns)
            for row in values:
                sheet.append(row)
            for row in sheet:
                for cell in row:
                    if isinstance(cell.value, str):
                        cell.data_type = "s"
            for cell in sheet[1]:
                cell.font = Font(color="FFFFFF", bold=True)
                cell.fill = PatternFill("solid", fgColor="2A4FDA")
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = 28
        meta = book.create_sheet("Definições")
        meta.append(["Gerado em UTC", data["as_of"]])
        meta.append(["Filtros", str(filters)])
        for rule in data["filters"]:
            meta.append(["Condição de campo", rule])
        for note in notes:
            meta.append(["Regra", note])
        meta.column_dimensions["A"].width = 28
        meta.column_dimensions["B"].width = 110
        book.properties.creator = "Gestão de Demandas"
        book.save(buffer)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        styles = getSampleStyleSheet()
        body = styles["BodyText"]
        body.fontSize = 8
        body.leading = 11

        def text(value):
            return Paragraph(escape(str(value if value is not None else "Indisponível")), body)

        def table(columns, rows, widths):
            result = Table(
                [[text(value) for value in columns]]
                + [[text(value) for value in row] for row in rows],
                colWidths=widths,
                repeatRows=1,
                hAlign="LEFT",
            )
            result.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8ecff")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d6dbe7")),
                    ]
                )
            )
            return result

        story = [
            Paragraph("Gestão de Demandas", styles["Title"]),
            Paragraph("Análise operacional de cards sprints e backlog", styles["Heading1"]),
            text("Gerado em UTC: " + data["as_of"]),
            text("Filtros: " + str(filters)),
        ]
        for rule in data["filters"] + notes:
            story.append(text(rule))
        story += [
            Spacer(1, 12),
            table(
                [
                    "ID",
                    "Card",
                    "Etapa",
                    "Fase atual (s)",
                    "Criação até 1ª conclusão (s)",
                    "Histórico",
                ],
                [
                    [
                        card["id"],
                        card["title"],
                        STATUSES[card["status"]],
                        card["current_phase_seconds"],
                        card["lead_time_seconds"],
                        "Completo" if card["history_complete"] else "Parcial",
                    ]
                    for card in cards
                ],
                [40, 260, 105, 100, 130, 90],
            ),
        ]
        story.append(Paragraph("Sprints no recorte", styles["Heading2"]))
        story.append(
            table(
                ["Sprint", "Iniciais", "Concluídos", "Pendentes", "Adicionados", "Devolvidos"],
                [
                    [
                        sprint["name"],
                        sprint["initial_cards"],
                        sprint["done"],
                        sprint["pending"],
                        sprint["added_after_start"],
                        sprint["returned"],
                    ]
                    for sprint in data["sprints"]
                ],
                [265, 90, 95, 90, 95, 90],
            )
        )
        for card in cards:
            story += [
                Spacer(1, 16),
                Paragraph(escape(f"OS-{card['id']} {card['title']}"), styles["Heading2"]),
                text("Fornecedor: " + str(card["supplier_name"] or "Não atribuído")),
                text(
                    "Prazo: "
                    + str(card["due"] or "Sem prazo")
                    + " | Horas utilizadas (min): "
                    + str(card["used_minutes"])
                ),
            ]
            if financial:
                story.append(
                    text("Custo consolidado (centavos): " + str(card.get("cost_cents", 0)))
                )
            for issue in card["history_issues"]:
                story.append(text(issue))
            story.append(
                table(
                    ["Etapa", "Entrada UTC", "Saída UTC", "Duração (s)", "Situação"],
                    [
                        [
                            STATUSES[period["status"]],
                            period["entered_at"],
                            period["exited_at"] or "Em aberto",
                            period["duration_seconds"],
                            "Comprovado" if period["complete"] else "Incompleto",
                        ]
                        for period in card["periods"]
                    ],
                    [110, 235, 235, 80, 65],
                )
            )
            for entry in card["approval_history"]:
                story.append(
                    text(
                        f"Horas v{entry['hours_version']}: {APPROVALS[entry['state']]} | Envio {entry['submitted_at']} | Decisão {entry['decision_at'] or 'Pendente'} | Espera (s): {entry['waiting_seconds']} | {entry['reason']}"
                    )
                )
            for event in card["timeline"]:
                story.append(
                    text(
                        f"{event['at']} | {event['actor']} | {event['action']} | {STATUSES.get(event['origin'], '')} → {STATUSES.get(event['destination'], '')} | {event['reason']}"
                    )
                )
        SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
            title="Análise operacional Gestão de Demandas",
            author="Gestão de Demandas",
        ).build(story)
        media = "application/pdf"
    buffer.seek(0)
    return buffer, media
