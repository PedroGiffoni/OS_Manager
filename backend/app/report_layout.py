"""Shared executive reading model. All values derive from the authorized report cohort."""

from decimal import Decimal


def decimal_text(value):
    return f"{Decimal(str(value)):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def executive(data, financial):
    cards, summary = data["items"], data["summary"]
    total = len(cards)
    done = sum(c["status"] == "done" for c in cards)
    completion = decimal_text(Decimal(done) * 100 / total) + "%" if total else "Sem base"
    used = sum(c["used_minutes"] for c in cards)
    approved = sum(c["approved_minutes"] for c in cards)
    estimated = sum(c["estimated_minutes"] or 0 for c in cards)
    kpis = [
        ("DEMANDAS", str(total), f"{summary['open']} em aberto · {done} concluídas", "primary"),
        ("CONCLUSÃO", completion, "Concluídas ÷ cards no recorte", "success"),
        ("EM ATRASO", str(summary["overdue"]), "Abertas com prazo vencido", "error"),
        (
            "APROVAÇÕES",
            str(summary["waiting_approval"]),
            "Submissões atuais aguardando decisão",
            "warning",
        ),
        (
            "HORAS UTILIZADAS",
            decimal_text(Decimal(used) / 60) + "h",
            f"{decimal_text(Decimal(approved) / 60)}h aprovadas",
            "secondary",
        ),
    ]
    if financial:
        cost = sum(c.get("cost_cents", 0) or 0 for c in cards)
        kpis.append(
            (
                "Custo consolidado",
                "R$ " + decimal_text(Decimal(cost) / 100),
                "Horas aprovadas × tarifa congelada",
                "primary",
            )
        )
    else:
        kpis.append(
            (
                "HISTÓRICO COMPLETO",
                str(summary["complete_histories"]),
                f"De {total} cards do recorte",
                "neutral",
            )
        )
    synth = [
        (
            "SITUAÇÃO",
            f"{done} de {total} demandas concluídas. {summary['open']} permanecem abertas no recorte selecionado.",
            "primary",
        ),
        (
            "ATENÇÃO",
            f"{summary['overdue']} demandas em atraso e {summary['waiting_approval']} submissões de horas aguardando aprovação.",
            "error",
        ),
        (
            "EVIDÊNCIA",
            f"{summary['complete_histories']} de {total} históricos completos. Durações sem evidência não são estimadas.",
            "success",
        ),
    ]
    return {
        "kpis": kpis,
        "synthesis": synth,
        "completion": completion,
        "total": total,
        "done": done,
        "hours": [("Previstas", estimated), ("Utilizadas", used), ("Aprovadas", approved)],
    }


def event_label(action):
    return {
        "created": "Card criado",
        "edited": "Dados do card editados",
        "assignment_changed": "Fornecedor alterado",
        "status_changed": "Etapa alterada",
        "hours_submitted": "Horas registradas",
        "hours_decided": "Horas avaliadas",
        "schema_versioned": "Configuração versionada",
        "values_versioned": "Campos atualizados",
        "reopened": "Card reaberto",
        "reordered": "Ordem alterada",
        "included_in_sprint": "Incluído em sprint",
        "returned_to_backlog": "Devolvido ao backlog",
        "comment_added": "Comentário adicionado",
        "attachment_added": "Anexo adicionado",
        "archived": "Card arquivado",
    }.get(action, action)
