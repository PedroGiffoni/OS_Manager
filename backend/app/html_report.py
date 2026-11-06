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
from .report_layout import executive, event_label

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
motion.addEventListener('click',()=>{const stopped=document.body.classList.toggle('paused');motion.setAttribute('aria-pressed',String(stopped));motion.textContent=stopped?'Ativar animações':'Pausar animações';});
document.getElementById('expand').addEventListener('click',()=>document.querySelectorAll('.card-detail').forEach(el=>el.open=true));
document.getElementById('collapse').addEventListener('click',()=>document.querySelectorAll('.card-detail').forEach(el=>el.open=false));
let closed=[];window.addEventListener('beforeprint',()=>{closed=[...document.querySelectorAll('.card-detail:not([open])')];closed.forEach(el=>el.open=true);});window.addEventListener('afterprint',()=>closed.forEach(el=>el.open=false));"""


def build_html(data, financial, filters):
    cards = data["items"]
    summary = data["summary"]
    logo = b64encode((ASSETS / "sebrae-white.svg").read_bytes()).decode()
    fonts = "".join(
        f"@font-face{{font-family:{family};src:url(data:font/woff2;base64,{b64encode((ASSETS / file).read_bytes()).decode()}) format('woff2');font-weight:{weight};font-display:swap}}"
        for family, file, weight in [
            ("Figtree", "figtree.woff2", 400),
            ("Figtree", "figtree-bold.woff2", 700),
            ("Lato", "lato.woff2", 400),
        ]
    )
    css = (ASSETS / "tokens.css").read_text(encoding="utf-8") + (ASSETS / "report.css").read_text(
        encoding="utf-8"
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
                ("Cumprimento: " + number(percent) + "%")
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
                event_label(t["action"]),
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
        f"{filter_labels.get(k, k)}: {datetime.fromisoformat(str(v)).strftime('%d/%m/%Y') if k in {'starts', 'ends'} else STATUSES.get(str(v), APPROVALS.get(str(v), v))}"
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
    reading = executive(data, financial)
    synthesis = "".join(
        f'<div class="tone-{tone}"><small>{e(title)}</small><p>{e(body)}</p></div>'
        for title, body, tone in reading["synthesis"]
    )
    kpis = "".join(
        f'<article class="kpi tone-{tone}"><p class="kpi-label">{e(label)}</p><strong>{e(value)}</strong><p class="kpi-note">{e(note)}</p></article>'
        for label, value, note, tone in reading["kpis"]
    )
    offset = Decimal(0)
    slices = ""
    legend = ""
    for state, label in STATUSES.items():
        count = sum(c["status"] == state for c in cards)
        pct = Decimal(count) * 100 / len(cards) if cards else Decimal(0)
        slices += (
            f'<circle class="slice state-{state}" cx="80" cy="80" r="55" pathLength="100" stroke-dasharray="{pct} {100 - pct}" stroke-dashoffset="{-offset}" />'
            if pct
            else ""
        )
        offset += pct
        legend += f'<li><span><i class="state-{state}" aria-hidden="true"></i>{e(label)}</span><strong>{count}</strong></li>'
    donut = f'<div class="donut-layout"><div class="donut"><svg viewBox="0 0 160 160" role="img" aria-label="Distribuição por etapa; valores na legenda"><circle class="donut-track" cx="80" cy="80" r="55"/>{slices}</svg><div><strong>{len(cards)}</strong><small>cards no recorte</small></div></div><ul class="legend">{legend}</ul></div>'
    effort = bars(
        [{"name": label, "minutes": minutes} for label, minutes in reading["hours"]],
        lambda r: r["name"],
        lambda r: r["minutes"],
        lambda v: number(Decimal(v) / 60) + "h",
    )
    insights = "".join(
        f'<article class="insight tone-{tone}"><small>{e(label)}</small><strong>{e(content)}</strong></article>'
        for label, content, tone in [
            ("PRAZOS", str(summary["overdue"]) + " cards abertos com prazo vencido.", "error"),
            (
                "RETRABALHO",
                str(summary["reopened"]) + " cards com reabertura registrada.",
                "warning",
            ),
            (
                "QUALIDADE DO HISTÓRICO",
                str(len(cards) - summary["complete_histories"])
                + " cards com informações históricas parciais.",
                "primary",
            ),
        ]
    )
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'sha256-{script_hash}'; base-uri 'none'; form-action 'none'">
<title>Relatório gerencial · Gestão de Demandas</title><style>{fonts}{css}</style></head>
<body><a class="skip" href="#conteudo">Ir para o relatório</a>
<header class="report-header"><img src="data:image/svg+xml;base64,{logo}" width="82" height="54" alt="Sebrae"><div class="header-title"><strong>Gestão de Demandas</strong><span>Relatório gerencial · Sebrae Ceará</span></div><div class="header-actions"><button id="motion" aria-pressed="false">Pausar animações</button><button id="print">Imprimir relatório</button></div></header>
<div class="report-shell"><nav class="report-nav" aria-label="Seções do relatório"><small>DECIDIR</small><a href="#resumo">01 · Panorama</a><small>GERIR</small><a href="#sprints">02 · Sprints</a><a href="#backlog">03 · Backlog</a><small>DETALHAR</small><a href="#cards">04 · Cards e históricos</a><a href="#metodo">05 · Critérios de leitura</a><div class="nav-foot">RETRATO EXPORTADO<br><strong>{e(stamp(data["as_of"]))}</strong><br>{e(APP_TIMEZONE)}</div></nav>
<main id="conteudo"><div class="report-context"><span><b>{len(cards)}</b> cards no recorte autorizado</span><ul class="chips" aria-label="Filtros aplicados">{chips}</ul></div>
<section id="resumo"><div class="section-head"><div><p class="eyebrow">01 / PANORAMA DA OPERAÇÃO</p><h1>Entregas em perspectiva</h1><p>Execução das demandas, pontos de atenção e evidências do fluxo.</p></div><span class="edition">Leitura: <b>Gestão</b> · {e(stamp(data["as_of"]))}</span></div>
<div class="synthesis">{synthesis}</div><div class="kpis">{kpis}</div>
<div class="grid g75"><article class="panel"><p class="eyebrow">DISTRIBUIÇÃO DA CARTEIRA</p><h2>Em que etapa estão as demandas?</h2><p>Quantidade de cards no recorte, sem metas ou avaliações individuais.</p>{donut}</article><div class="insight-stack"><p class="eyebrow">SINAIS DESTA FOTOGRAFIA</p>{insights}</div></div>
<div class="grid"><article class="panel"><p class="eyebrow">TEMPO DO FLUXO</p><h2>Onde o trabalho permanece</h2><p>Soma das permanências comprovadas por fase.</p>{phases}<p class="chart-note">Tempo corrido, incluindo noites e fins de semana. Não equivale a esforço apontado. Concluído é terminal.</p></article><article class="panel"><p class="eyebrow">ESFORÇO REGISTRADO</p><h2>Planejamento e realização</h2><p>Totais de horas previstas, utilizadas e aprovadas.</p>{effort}<p class="chart-note">Estimativas ausentes não entram no planejamento. Horas utilizadas ainda não aprovadas não integram o custo consolidado.</p></article></div></section>
<section id="sprints"><div class="section-head"><div><p class="eyebrow">02 / RITMO DAS ENTREGAS</p><h2>Ritmo das sprints</h2><p>Compromisso inicial, entradas posteriores e resultado no recorte.</p></div></div><div class="sprint-grid">{sprint_cards}</div></section>
<section id="backlog"><div class="section-head"><div><p class="eyebrow">03 / TRABALHO A PLANEJAR</p><h2>Saúde do backlog</h2><p>Volume, responsabilidades e envelhecimento da fila.</p></div></div><div class="metrics">{metric("No backlog", backlog["count"])}{metric("Sem fornecedor", backlog["unassigned"])}{metric("Em atraso", backlog["overdue"])}{metric("Sem alteração observada", backlog["idle"], str(backlog["idle_days"]) + " dias ou mais")}</div><article class="panel"><h3>Mais antigos primeiro</h3>{table(["Card", "Título", "Idade do registro", "Na fase atual"], [[f"OS-{c["id"]}", c["title"], duration(c["age_seconds"]), duration(c["current_phase_seconds"])] for c in data["backlog_oldest"]], "Até dez itens mais antigos do backlog")}</article></section>
<section id="cards"><div class="section-head"><div><p class="eyebrow">04 / RASTREABILIDADE</p><h2>Explore as demandas</h2><p>Da lista consolidada ao histórico individual de fases e aprovações.</p></div><div class="actions"><button id="expand">Expandir cards</button><button id="collapse">Recolher cards</button></div></div><article class="panel">{table(["ID", "Atividade", "Etapa", "Fornecedor", "Na fase atual", "Até primeira conclusão"] + (["Custo consolidado"] if financial else []), card_rows, "Cards do recorte")}</article>{details or '<p class="empty">Nenhum card encontrado para os filtros selecionados.</p>'}</section>
<section id="metodo" class="panel methodology"><p class="eyebrow">05 / TRANSPARÊNCIA DOS INDICADORES</p><h2>Como ler este relatório</h2><div class="method-grid"><div><h3>Conclusão e prazo</h3><p>Conclusão = concluídas ÷ cards no recorte × 100. Sem base, não há percentual. Cards sem prazo não são classificados em atraso.</p></div><div><h3>Tempo e evidência</h3><p>Lead time vai da criação à primeira conclusão. Reaberturas preservam ciclos. {summary["complete_histories"]} de {len(cards)} históricos completos; sem evidência, duração indisponível.</p></div><div><h3>Escopo temporal</h3><p>{e(data["period_basis"])} {e(summary["recorded_flow"]["basis"])}</p></div><div><h3>Permissões e compartilhamento</h3><p>Retrato estático gerado com as permissões do emissor. Não atualiza automaticamente. Compartilhe somente com pessoas autorizadas.</p></div></div></section>
<footer><strong>Gestão de Demandas · Sebrae Ceará</strong><span>Dados observados até {e(stamp(data["as_of"]))} · {e(APP_TIMEZONE)}</span></footer></main></div><script>{SCRIPT}</script></body></html>"""
    return BytesIO(html.encode("utf-8")), "text/html"
