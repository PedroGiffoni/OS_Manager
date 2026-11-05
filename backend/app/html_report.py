"""Standalone, offline report. Only explicitly selected data is rendered; never dump API payloads."""

from base64 import b64encode
from decimal import Decimal
from hashlib import sha256
from html import escape
from io import BytesIO
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from .report_filters import STATUSES, APPROVALS
from .settings import APP_TIMEZONE

ASSETS = Path(__file__).parent / "report_assets"


def e(value):
    return escape(str(value if value is not None else "Indisponível"), quote=True)


def number(value):
    return f"{Decimal(str(value or 0)):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def duration(value):
    if value is None:
        return "Indisponível"
    value = int(value)
    days, value = divmod(value, 86400)
    hours, value = divmod(value, 3600)
    minutes, seconds = divmod(value, 60)
    return (
        " ".join(
            f"{n}{unit}"
            for n, unit in [(days, "d"), (hours, "h"), (minutes, "min"), (seconds, "s")]
            if n
        )
        or "0s"
    )


def stamp(value):
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(ZoneInfo(APP_TIMEZONE))
        return parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(value)


def table(headers, rows, caption):
    content = "".join(
        "<tr>" + "".join(f"<td>{e(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    if not content:
        content = f'<tr><td colspan="{len(headers)}">Nenhum registro neste recorte.</td></tr>'
    return (
        f'<div class="table-scroll" tabindex="0" role="region" aria-label="{e(caption)}"><table><caption>{e(caption)}</caption><thead><tr>'
        + "".join(f'<th scope="col">{e(h)}</th>' for h in headers)
        + "</tr></thead><tbody>"
        + content
        + "</tbody></table></div>"
    )


def metric(label, value, note=""):
    return f'<article class="metric"><p>{e(label)}</p><strong>{e(value)}</strong><small>{e(note)}</small></article>'


def bars(rows, label, value, formatter=str):
    maximum = max([value(row) or 0 for row in rows], default=0) or 1
    return (
        '<div class="bars">'
        + "".join(
            f'<div class="bar-row"><div><span>{e(label(row))}</span><strong>{e(formatter(value(row)))}</strong></div><div class="track" aria-hidden="true"><span style="width:{max(0, min(100, (value(row) or 0) * 100 // maximum))}%"></span></div></div>'
            for row in rows
        )
        + "</div>"
    )


SCRIPT = """document.getElementById('print').addEventListener('click',()=>window.print());
const motion=document.getElementById('motion');
motion.addEventListener('click',()=>{const stopped=document.body.classList.toggle('paused');motion.setAttribute('aria-pressed',String(stopped));motion.textContent=stopped?'Ativar animações':'Pausar animações';});"""


def build_html(data, financial, filters):
    cards = data["items"]
    summary = data["summary"]
    done = sum(card["status"] == "done" for card in cards)
    completion = f"{number(Decimal(done) * 100 / len(cards))}%" if cards else "Sem dados"
    logo = b64encode((ASSETS / "sebrae-cor.svg").read_bytes()).decode()
    fonts = "".join(
        f"@font-face{{font-family:{family};src:url(data:font/woff2;base64,{b64encode((ASSETS / file).read_bytes()).decode()}) format('woff2');font-weight:100 900;font-display:swap}}"
        for family, file in [("Figtree", "figtree.woff2"), ("Lato", "lato.woff2")]
    )
    css = (ASSETS / "tokens.css").read_text(encoding="utf-8") + (ASSETS / "report.css").read_text(
        encoding="utf-8"
    )
    overview = (
        metric("Cards no recorte", len(cards), "Escopo autorizado e filtrado")
        + metric("Conclusão", completion, f"{done} cards concluídos")
        + metric("Em atraso", summary["overdue"], "Cards abertos com prazo vencido")
        + metric("Aguardando aprovação", summary["waiting_approval"], "Submissões atuais pendentes")
    )
    if financial:
        overview += metric(
            "Custo consolidado",
            "R$ " + number(Decimal(sum(c.get("cost_cents", 0) or 0 for c in cards)) / 100),
            "Somente horas aprovadas · tarifa congelada",
        )
    status_chart = bars(
        summary["by_status"], lambda r: STATUSES.get(r["value"], r["value"]), lambda r: r["count"]
    )
    phases = bars(
        summary["phase_seconds"],
        lambda r: STATUSES[r["status"]],
        lambda r: r["duration_seconds"],
        duration,
    )
    sprint_cards = ""
    for sprint in data["sprints"]:
        percent = sprint["commitment_percent"]
        sprint_cards += (
            f'<article class="panel"><h3>{e(sprint["name"])}</h3><p>Estado: {e({"planned": "Planejada", "active": "Ativa", "closed": "Encerrada"}.get(sprint["state"], sprint["state"]))} · Observado até {e(stamp(sprint["as_of"]))}</p><div class="metrics">'
            + metric(
                "Compromisso inicial",
                sprint["initial_cards"],
                "Base conhecida" if sprint["history_complete"] else "Histórico parcial",
            )
            + metric(
                "Iniciais concluídos",
                sprint["initial_done"],
                ("Cumprimento: " + str(percent) + "%")
                if percent is not None
                else "Percentual indisponível",
            )
            + metric("Adicionados após início", sprint["added_after_start"])
            + metric("Devolvidos", sprint["returned"])
            + "</div>"
        )
        sprint_cards += (
            bars(
                [
                    {"name": "Concluídos", "n": sprint["done"]},
                    {"name": "Pendentes", "n": sprint["pending"]},
                ],
                lambda r: r["name"],
                lambda r: r["n"],
            )
            + "</article>"
        )
    if not sprint_cards:
        sprint_cards = '<p class="empty">Nenhuma sprint neste recorte.</p>'
    details = ""
    for card in cards:
        finance = (
            "<p><strong>Custo consolidado:</strong> R$ "
            + number(Decimal(card.get("cost_cents", 0) or 0) / 100)
            + "</p>"
            if financial
            else ""
        )
        detail_rows = [
            [
                STATUSES[p["status"]],
                stamp(p["entered_at"]),
                stamp(p["exited_at"]) if p["exited_at"] else "Em aberto",
                duration(p["duration_seconds"]),
                "Comprovado" if p["complete"] else "Parcial",
            ]
            for p in card["periods"]
        ]
        events = [
            [
                stamp(t["at"]),
                t["actor"],
                t["action"],
                STATUSES.get(t["origin"], "—"),
                STATUSES.get(t["destination"], "—"),
                t["reason"],
            ]
            for t in card["timeline"]
        ]
        approvals = [
            [
                a["hours_version"],
                APPROVALS[a["state"]],
                number(Decimal(a["used_minutes"]) / 60),
                stamp(a["submitted_at"]),
                stamp(a["decision_at"]),
                duration(a["waiting_seconds"]),
                a["reason"],
            ]
            for a in card["approval_history"]
        ]
        additional = [
            [f["label"], card["values"].get(f["id"], "Não preenchido")]
            for f in card["fields"]
            if f.get("id") in card["values"]
        ]
        details += f'<details class="panel card-detail"><summary>OS-{card["id"]} · {e(card["title"])}</summary><div class="detail-body"><p>{e(STATUSES[card["status"]])} · {e(card["supplier_name"] or "Sem fornecedor")} · Observado até {e(stamp(card["as_of"]))}</p>'
        if not card["history_complete"]:
            details += (
                '<aside class="notice">Histórico parcial: '
                + e("; ".join(card["history_issues"]))
                + "</aside>"
            )
        details += (
            '<div class="metrics">'
            + metric("Idade do registro", duration(card["age_seconds"]))
            + metric("Até primeira conclusão", duration(card["lead_time_seconds"]))
            + metric("Reaberturas", card["reopen_count"])
            + metric("Horas utilizadas", number(Decimal(card["used_minutes"]) / 60))
            + metric(
                "Horas previstas",
                number(Decimal(card["estimated_minutes"]) / 60)
                if card["estimated_minutes"]
                else "Sem estimativa",
            )
            + metric("Horas aprovadas", number(Decimal(card["approved_minutes"]) / 60))
            + metric(
                "Desvio de horas",
                number(Decimal(card["hours_deviation_minutes"]) / 60)
                if card["hours_deviation_minutes"] is not None
                else "Sem estimativa",
            )
            + metric(
                "Prazo",
                card["due"]
                and datetime.fromisoformat(card["due"]).strftime("%d/%m/%Y")
                or "Sem prazo",
            )
            + "</div>"
            + finance
        )
        details += (
            table(
                ["Etapa", "Entrada", "Saída", "Permanência", "Evidência"],
                detail_rows,
                "Passagens por fase",
            )
            + table(
                [
                    "Versão",
                    "Decisão",
                    "Horas utilizadas",
                    "Envio",
                    "Decisão em",
                    "Espera",
                    "Justificativa",
                ],
                approvals,
                "Histórico de aprovações",
            )
            + table(
                ["Instante", "Autor", "Evento", "Origem", "Destino", "Justificativa"],
                events,
                "Linha do tempo",
            )
        )
        details += (
            table(["Campo", "Valor"], additional, "Campos adicionais visíveis preenchidos")
            + "</div></details>"
        )
    filter_labels = {
        "status": "Etapa",
        "sprint_id": "Sprint ID",
        "supplier_id": "Fornecedor ID",
        "starts": "Criados desde",
        "ends": "Criados até",
        "min_phase_hours": "Permanência mínima (h)",
        "overdue_only": "Somente atrasados",
        "only_reopened": "Somente reabertos",
        "approval_state": "Aprovação",
        "idle_days": "Sem alteração (dias)",
    }
    applied = [
        f"{filter_labels.get(k, k)}: {v}"
        for k, v in filters.items()
        if k != "campos" and v not in (None, "", False)
    ] + data["filters"]
    chips = (
        "".join(f"<li>{e(v)}</li>" for v in applied)
        or "<li>Todos os registros do escopo autorizado</li>"
    )
    card_rows = [
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
    backlog = summary["backlog"]
    script_hash = b64encode(sha256(SCRIPT.encode()).digest()).decode()
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; base-uri 'none'; form-action 'none'"><title>Relatório · Gestão de Demandas</title><style>{fonts}{css}</style></head><body><a class="skip" href="#conteudo">Ir para o relatório</a><header><img src="data:image/svg+xml;base64,{logo}" width="100" height="64" alt="Sebrae"><div><p class="eyebrow">SEBRAE CEARÁ · GESTÃO DE DEMANDAS</p><p>Inteligência operacional</p></div></header><nav aria-label="Seções do relatório"><a href="#resumo">Resumo</a><a href="#sprints">Sprints</a><a href="#backlog">Backlog</a><a href="#cards">Cards</a><button id="motion" aria-pressed="false">Pausar animações</button><button id="print">Imprimir relatório</button></nav><main id="conteudo"><section id="resumo"><p class="eyebrow">RELATÓRIO EXECUTIVO E OPERACIONAL</p><h1>Entregas em perspectiva</h1><p class="lead">Do panorama da operação ao histórico de cada demanda.</p><p>Gerado em {e(stamp(data["as_of"]))} · Fuso de apresentação: {e(APP_TIMEZONE)} · Retrato estático, sem atualização automática.</p><ul class="chips" aria-label="Filtros aplicados">{chips}</ul><div class="metrics">{overview}</div><div class="grid"><article class="panel"><h2>Distribuição das demandas</h2><p>Quantidade de cards por etapa no recorte.</p>{status_chart}</article><article class="panel"><h2>Onde o fluxo permanece</h2><p>Soma dos tempos comprovados em cada fase; concluído é terminal.</p>{phases}</article></div><aside class="notice">Permanência é tempo corrido, incluindo noites e fins de semana. Não representa horas trabalhadas ou faturáveis. {summary["complete_histories"]} de {len(cards)} cards têm histórico completo. Sem evidência, a duração é indisponível.</aside></section><section id="sprints"><h2>Ritmo das sprints</h2><p>Compromisso inicial, mudanças de escopo e entregas, considerando somente o recorte autorizado.</p>{sprint_cards}</section><section id="backlog"><h2>Saúde do backlog</h2><div class="metrics">{metric("No backlog", backlog["count"])}{metric("Sem fornecedor", backlog["unassigned"])}{metric("Em atraso", backlog["overdue"])}{metric("Sem alteração observada", backlog["idle"], str(backlog["idle_days"]) + " dias ou mais")}</div><article class="panel"><h3>Cards mais antigos do backlog</h3>{table(["Card", "Título", "Idade", "Fase atual"], [[f"OS-{c["id"]}", c["title"], duration(c["age_seconds"]), duration(c["current_phase_seconds"])] for c in data["backlog_oldest"]], "Até dez itens mais antigos")}</article></section><section id="cards"><h2>Explore as demandas</h2><p>Abra cada card para consultar fases, decisões de horas e eventos.</p>{table(["ID", "Atividade", "Etapa", "Fornecedor", "Na fase atual", "Até primeira conclusão"] + (["Custo consolidado"] if financial else []), card_rows, "Cards do recorte")}{details or '<p class="empty">Nenhum card encontrado para os filtros selecionados.</p>'}</section><section class="panel"><h2>Como ler os indicadores</h2><ul><li>Conclusão = cards concluídos ÷ cards no recorte × 100. Base zero: sem dados.</li><li>Lead time: criação até a primeira conclusão, quando comprovado pelo histórico.</li><li>Reaberturas preservam ciclos separados. Fases encerradas de sprint respeitam seu corte histórico.</li><li>{e(data["period_basis"])}</li><li>{e(summary["recorded_flow"]["basis"])}</li><li>Dados e campos respeitam as permissões de quem gerou este arquivo. Compartilhe somente com pessoas autorizadas.</li></ul></section></main><footer><strong>Gestão de Demandas · Sebrae Ceará</strong><p>Relatório portátil · Dados observados até {e(stamp(data["as_of"]))}</p></footer><script>{SCRIPT}</script></body></html>"""
    return BytesIO(html.encode("utf-8")), "text/html"
