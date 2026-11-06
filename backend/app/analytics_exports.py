from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from .report_filters import STATUSES, APPROVALS


def build_export(format, data, financial, filters):
    if format == "html":
        from .html_report import build_html

        return build_html(data, financial, filters)
    if format == "pdf":
        from .pdf_report import build_pdf

        return build_pdf(data, financial, filters)
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
                STATUSES.get(card["status"], card["status"]),
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
                STATUSES.get(period["status"], period["status"]),
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
    buffer.seek(0)
    return buffer, media
