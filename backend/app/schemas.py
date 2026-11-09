from typing import Literal
from datetime import date
import re
import math
from pydantic import BaseModel, Field, ConfigDict, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class NotificationPreferenceInput(Input):
    email: str | None = Field(default=None, max_length=254)
    email_enabled: StrictBool = False

    @model_validator(mode="after")
    def validate_email_preference(self):
        if self.email is not None and not re.fullmatch(
            r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", self.email
        ):
            raise ValueError("Informe um endereço de e-mail válido.")
        if self.email_enabled and not self.email:
            raise ValueError("Informe um e-mail para ativar as notificações.")
        return self


class UserProfileInput(Input):
    display_name: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=254)
    contact_phone: str = Field(default="", max_length=40)

    @model_validator(mode="after")
    def validate_contacts(self):
        if self.contact_email and not re.fullmatch(
            r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", self.contact_email
        ):
            raise ValueError("Informe um endereço de e-mail válido.")
        if self.contact_phone and not re.fullmatch(r"[0-9+().\-\s]{1,40}", self.contact_phone):
            raise ValueError("Informe um telefone válido.")
        return self


class PushSubscriptionKeys(Input):
    p256dh: str = Field(min_length=40, max_length=180)
    auth: str = Field(min_length=16, max_length=100)


class PushSubscriptionInput(Input):
    endpoint: str = Field(min_length=1, max_length=2048)
    keys: PushSubscriptionKeys


class UserInput(Input):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    role: str
    grants: list[str] = []


class SupplierInput(Input):
    name: str = Field(min_length=1, max_length=160)
    function: str = Field(min_length=1, max_length=160)
    user_id: StrictInt | None = None
    active: bool = True


class RateInput(Input):
    cents: StrictInt = Field(gt=0, le=100000000)
    reason: str = Field(default="", max_length=500)


class Version(Input):
    version: StrictInt = Field(gt=0)


class TaskLabel(Input):
    text: str = Field(min_length=1, max_length=40)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class TaskInput(Input):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=10000)
    supplier_id: StrictInt | None = None
    assignee_user_id: StrictInt | None = None
    due: date | None = None
    priority: StrictInt = 0
    work_type: Literal["epic", "story", "task", "bug", "subtask"] = "task"
    parent_id: StrictInt | None = None
    labels: list[TaskLabel] | None = Field(default=None, max_length=8)

    @model_validator(mode="after")
    def unique_label_texts(self):
        texts = [label.text.casefold() for label in self.labels or []]
        if len(texts) != len(set(texts)):
            raise ValueError("As etiquetas precisam ter textos diferentes.")
        return self


class TaskCreate(TaskInput):
    estimate_policy: Literal["absent", "optional", "required"] = "absent"


class TaskEdit(TaskInput):
    version: StrictInt = Field(gt=0)


class Move(Version):
    status: str
    priority: StrictInt = 0
    reason: str = Field(default="", max_length=1000)
    resolution: Literal["Done", "Fixed", "Duplicate", "Won't Do", "Cannot Reproduce", "Other"] = "Done"


class KanbanColumnCreate(Input):
    title: str = Field(min_length=1, max_length=100)


class KanbanColumnRename(Input):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    category: Literal["todo", "in_progress", "done"] | None = None
    wip_limit: StrictInt | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def has_column_update(self):
        if self.title is None and self.category is None and "wip_limit" not in self.model_fields_set:
            raise ValueError("Informe o título, a categoria ou o limite de WIP da coluna.")
        return self


class KanbanColumnOrder(Input):
    keys: list[str] = Field(min_length=5, max_length=30)


class SavedViewInput(Input):
    name: str = Field(min_length=1, max_length=80)
    layout: Literal["board", "table", "timeline", "calendar"] = "board"
    config: dict = Field(default_factory=dict)
    shared: bool = False
    shared_roles: list[Literal["admin", "manager", "internal"]] = Field(
        default_factory=list, max_length=3
    )
    shared_group_ids: list[StrictInt] = Field(default_factory=list, max_length=50)
    position: StrictInt = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def valid_sharing(self):
        if self.shared and not (self.shared_roles or self.shared_group_ids):
            raise ValueError("Selecione ao menos um papel ou grupo para compartilhar a visualização.")
        if not self.shared and (self.shared_roles or self.shared_group_ids):
            raise ValueError("Papéis e grupos exigem que a visualização esteja compartilhada.")
        if any(identity <= 0 for identity in self.shared_group_ids) or len(set(self.shared_group_ids)) != len(self.shared_group_ids):
            raise ValueError("A lista de grupos compartilhados contém IDs inválidos ou repetidos.")
        return self


class SavedFilterInput(Input):
    name: str = Field(min_length=1, max_length=100)
    query: str = Field(max_length=1000)
    shared: bool = False
    shared_roles: list[Literal["admin", "manager", "internal"]] = Field(
        default_factory=list, max_length=3
    )
    shared_group_ids: list[StrictInt] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid_saved_filter(self):
        self.query = self.query.strip()
        if not self.query:
            raise ValueError("Informe uma consulta para salvar o filtro.")
        if self.shared and not (self.shared_roles or self.shared_group_ids):
            raise ValueError("Selecione ao menos um papel ou grupo para compartilhar o filtro.")
        if not self.shared and (self.shared_roles or self.shared_group_ids):
            raise ValueError("Papéis e grupos exigem que o filtro esteja compartilhado.")
        if len(set(self.shared_roles)) != len(self.shared_roles):
            raise ValueError("Não repita papéis no compartilhamento do filtro.")
        if any(identity <= 0 for identity in self.shared_group_ids) or len(set(self.shared_group_ids)) != len(self.shared_group_ids):
            raise ValueError("A lista de grupos compartilhados contém IDs inválidos ou repetidos.")
        if self.shared and re.search(r"\bfield_[a-zA-Z]|\btext\s*~", self.query, re.IGNORECASE):
            raise ValueError("Filtros compartilhados não podem consultar valores de campos personalizados ou texto amplo.")
        return self


class UserGroupInput(Input):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    active: bool = True


class UserGroupMembersInput(Input):
    user_ids: list[StrictInt] = Field(max_length=500)

    @model_validator(mode="after")
    def unique_users(self):
        if any(identity <= 0 for identity in self.user_ids) or len(set(self.user_ids)) != len(self.user_ids):
            raise ValueError("A lista de usuários contém IDs inválidos ou repetidos.")
        return self


class ReleaseInput(Input):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    starts: date | None = None
    due: date | None = None

    @model_validator(mode="after")
    def valid_dates(self):
        if self.starts and self.due and self.due < self.starts:
            raise ValueError("O prazo da versão deve ser igual ou posterior ao início.")
        return self


class ComponentInput(Input):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    owner_id: StrictInt | None = None
    active: bool = True


class TaskLinkInput(Input):
    target_task_id: StrictInt = Field(gt=0)
    link_type: Literal["blocks", "relates", "duplicates"]


class CapacityInput(Input):
    supplier_id: StrictInt | None = None
    user_id: StrictInt | None = None
    group_id: StrictInt | None = None
    starts: date
    ends: date
    minutes: StrictInt = Field(ge=0, le=10000000)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def valid_resource_and_range(self):
        if sum(value is not None for value in (self.supplier_id, self.user_id, self.group_id)) != 1:
            raise ValueError("Selecione exatamente um fornecedor, usuário ou equipe.")
        if any(value is not None and value <= 0 for value in (self.supplier_id, self.user_id, self.group_id)):
            raise ValueError("O recurso selecionado precisa ter ID positivo.")
        if self.ends < self.starts:
            raise ValueError("O término deve ser igual ou posterior ao início.")
        return self


class CapacityLevelingApply(Input):
    expected_plan_version: StrictInt = Field(ge=0)


class CalendarExportInput(Input):
    task_ids: list[StrictInt] = Field(max_length=5000)

    @model_validator(mode="after")
    def validate_task_ids(self):
        if any(identity <= 0 for identity in self.task_ids):
            raise ValueError("Os IDs dos cards devem ser positivos.")
        if len(self.task_ids) != len(set(self.task_ids)):
            raise ValueError("Não repita cards no calendário.")
        return self


class WorkflowTypeRule(Input):
    enabled: bool = True
    roles: list[Literal["admin", "manager", "internal", "supplier"]] = Field(
        default_factory=list, max_length=4
    )
    required_fields: list[str] = Field(default_factory=list, max_length=20)
    conditions: list[dict] = Field(default_factory=list, max_length=10)
    actions: list[dict] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def unique_values(self):
        if len(self.roles) != len(set(self.roles)):
            raise ValueError("Não repita perfis na regra do tipo de card.")
        if len(self.required_fields) != len(set(self.required_fields)):
            raise ValueError("Não repita campos na regra do tipo de card.")
        if any(not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]{0,49}$", value) for value in self.required_fields):
            raise ValueError("Identificador de campo adicional inválido.")
        for condition in self.conditions:
            WorkflowCondition.model_validate(condition)
        for action in self.actions:
            WorkflowAction.model_validate(action)
        return self


class WorkflowCondition(Input):
    field: Literal["approval", "work_type", "priority", "supplier_assigned", "label", "due_set", "due_overdue", "due_within_days", "parent_set", "assignee", "release_assigned", "component_assigned", "blocked", "custom_field_equals"]
    operator: Literal["eq", "not_eq", "gte", "lte"]
    value: StrictStr | StrictInt | StrictBool | StrictFloat
    custom_field_id: str | None = None

    @model_validator(mode="after")
    def valid_condition_value(self):
        if self.field == "custom_field_equals":
            if (
                not self.custom_field_id
                or not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]{0,79}$", self.custom_field_id)
                or self.operator not in {"eq", "not_eq"}
                or isinstance(self.value, float) and not math.isfinite(self.value)
                or isinstance(self.value, str) and len(self.value) > 1000
            ):
                raise ValueError("Condição de campo personalizado exige ID, valor escalar e igualdade.")
        elif self.custom_field_id is not None:
            raise ValueError("custom_field_id só pode ser usado em custom_field_equals.")
        elif self.field == "priority":
            if type(self.value) is not int:
                raise ValueError("Condição de prioridade exige número inteiro.")
        elif self.field == "supplier_assigned":
            if type(self.value) is not bool or self.operator not in {"eq", "not_eq"}:
                raise ValueError("Condição de fornecedor exige verdadeiro/falso e igualdade.")
        elif self.field == "due_overdue":
            if type(self.value) is not bool or self.operator not in {"eq", "not_eq"}:
                raise ValueError("Condição de atraso exige verdadeiro/falso e igualdade.")
        elif self.field == "due_within_days":
            if type(self.value) is not int or not 0 <= self.value <= 3650 or self.operator not in {"eq", "not_eq"}:
                raise ValueError("A janela de prazo exige de 0 a 3.650 dias e igualdade.")
        elif self.field in {"due_set", "parent_set", "release_assigned", "component_assigned", "blocked"}:
            if type(self.value) is not bool or self.operator not in {"eq", "not_eq"}:
                raise ValueError("Condição de vínculo, prazo, hierarquia ou bloqueio exige verdadeiro/falso e igualdade.")
        elif self.field == "assignee":
            if type(self.value) is not int or self.value <= 0 or self.operator not in {"eq", "not_eq"}:
                raise ValueError("Condição de responsável exige o ID positivo de uma conta interna.")
        elif self.field == "label":
            if not isinstance(self.value, str) or not 1 <= len(self.value) <= 40 or self.operator not in {"eq", "not_eq"}:
                raise ValueError("Condição de etiqueta exige um texto de até 40 caracteres e igualdade.")
        else:
            allowed = (
                {"pending", "approved", "rejected", "resubmitted"}
                if self.field == "approval"
                else {"epic", "story", "task", "bug", "subtask"}
            )
            if not isinstance(self.value, str) or self.value not in allowed or self.operator not in {"eq", "not_eq"}:
                raise ValueError("Valor ou operador inválido para a condição de workflow.")
        return self


class WorkflowAction(Input):
    action: Literal["set_priority", "add_label", "remove_label", "add_comment", "set_due_after_days", "assign_internal_user", "add_watcher", "set_custom_fields"]
    config: dict

    @model_validator(mode="after")
    def valid_action_config(self):
        if self.action == "set_priority":
            if (
                set(self.config) != {"priority"}
                or type(self.config["priority"]) is not int
                or not -100000 <= self.config["priority"] <= 100000
            ):
                raise ValueError("A ação de prioridade exige somente um inteiro dentro do limite.")
        elif self.action == "add_label":
            if (
                set(self.config) != {"text", "color"}
                or not isinstance(self.config["text"], str)
                or not 1 <= len(self.config["text"].strip()) <= 40
                or not isinstance(self.config["color"], str)
                or not re.fullmatch(r"#[0-9A-Fa-f]{6}", self.config["color"])
            ):
                raise ValueError("A ação de etiqueta exige texto e cor hexadecimal válidos.")
        elif self.action == "remove_label":
            if (
                set(self.config) != {"text"}
                or not isinstance(self.config["text"], str)
                or not 1 <= len(self.config["text"].strip()) <= 40
            ):
                raise ValueError("A ação de remoção exige o texto de uma etiqueta de até 40 caracteres.")
        elif self.action == "set_due_after_days":
            if (
                set(self.config) != {"days"}
                or type(self.config["days"]) is not int
                or not 0 <= self.config["days"] <= 3650
            ):
                raise ValueError("A ação de prazo exige dias corridos entre 0 e 3.650.")
        elif self.action in {"assign_internal_user", "add_watcher"}:
            if (
                set(self.config) != {"user_id"}
                or type(self.config["user_id"]) is not int
                or self.config["user_id"] <= 0
            ):
                raise ValueError("A ação exige o ID positivo de uma conta interna.")
        elif self.action == "set_custom_fields":
            values = self.config.get("values")
            if set(self.config) != {"values"} or not isinstance(values, dict) or not 1 <= len(values) <= 10:
                raise ValueError("A ação de campos exige de 1 a 10 valores personalizados.")
            if any(
                not isinstance(identity, str)
                or not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]{0,79}$", identity)
                or not (value is None or isinstance(value, (str, bool, int, float)))
                or isinstance(value, str) and len(value) > 10000
                or isinstance(value, float) and not math.isfinite(value)
                for identity, value in values.items()
            ):
                raise ValueError("A ação contém um ID inválido ou um valor não escalar.")
        elif (
            set(self.config) != {"body"}
            or not isinstance(self.config["body"], str)
            or not 1 <= len(self.config["body"].strip()) <= 1000
        ):
            raise ValueError("A ação de comentário exige texto simples de até 1.000 caracteres.")
        return self


class WorkflowTransitionInput(Input):
    source: str = Field(min_length=1, max_length=60)
    target: str = Field(min_length=1, max_length=60)
    enabled: bool = True
    roles: list[Literal["admin", "manager", "internal", "supplier"]] = Field(
        default_factory=list, max_length=4
    )
    work_types: list[Literal["epic", "story", "task", "bug", "subtask"]] = Field(
        default_factory=list, max_length=5
    )
    required_fields: list[str] = Field(default_factory=list, max_length=20)
    type_rules: dict[Literal["epic", "story", "task", "bug", "subtask"], WorkflowTypeRule] = Field(
        default_factory=dict, max_length=5
    )
    conditions: list[WorkflowCondition] = Field(default_factory=list, max_length=10)
    actions: list[WorkflowAction] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def unique_work_types(self):
        if len(self.work_types) != len(set(self.work_types)):
            raise ValueError("Não repita tipos de card na regra de transição.")
        if len(self.required_fields) != len(set(self.required_fields)):
            raise ValueError("Não repita campos obrigatórios.")
        if any(not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]{0,49}$", value) for value in self.required_fields):
            raise ValueError("Identificador de campo adicional inválido.")
        return self


class AutomationRuleInput(Input):
    name: str = Field(min_length=1, max_length=120)
    trigger: Literal[
        "card_created",
        "task_updated",
        "field_changed",
        "assignee_changed",
        "due_changed",
        "priority_changed",
        "status_changed",
        "comment_added",
        "attachment_added",
        "link_added",
        "link_removed",
        "hours_submitted",
        "hours_decided",
        "sprint_started",
        "sprint_completed",
        "sprint_scope_changed",
        "development_event",
        "scheduled_daily",
    ]
    schedule_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    schedule_frequency: Literal["daily", "weekly"] = "daily"
    schedule_weekdays: list[StrictInt] = Field(default_factory=list, max_length=7)
    conditions: dict = Field(default_factory=dict)
    action: Literal["set_priority", "add_label", "remove_label", "add_comment", "set_due_after_days", "assign_internal_user", "add_watcher", "set_custom_fields"] | None = None
    config: dict = Field(default_factory=dict)
    actions: list[WorkflowAction] = Field(default_factory=list, max_length=10)
    enabled: bool = True

    @model_validator(mode="after")
    def safe_automation(self):
        if (self.trigger == "scheduled_daily") != (self.schedule_time is not None):
            raise ValueError("Automação agendada exige horário UTC; outros gatilhos não aceitam horário.")
        if self.trigger == "scheduled_daily":
            if self.schedule_frequency == "weekly":
                if (
                    not self.schedule_weekdays
                    or any(day < 0 or day > 6 for day in self.schedule_weekdays)
                    or len(self.schedule_weekdays) != len(set(self.schedule_weekdays))
                ):
                    raise ValueError("Selecione dias da semana únicos, de segunda-feira (0) a domingo (6).")
                self.schedule_weekdays.sort()
            elif self.schedule_weekdays:
                raise ValueError("Dias da semana só podem ser definidos para recorrência semanal.")
        elif self.schedule_frequency != "daily" or self.schedule_weekdays:
            raise ValueError("Recorrência e dias da semana só se aplicam ao gatilho agendado.")
        allowed_conditions = {"statuses", "work_types", "priority_min", "priority_max", "labels", "approval_states", "due_set", "assignee_user_ids", "overdue", "due_within_days", "release_assigned", "component_assigned", "blocked", "development_providers", "development_event_types", "development_states", "comment_contains", "attachment_media_types", "link_types", "changed_fields", "sprint_scope_actions", "custom_field_equals"}
        if set(self.conditions) - allowed_conditions:
            raise ValueError("Condição de automação não suportada.")
        custom_fields = self.conditions.get("custom_field_equals", {})
        if (
            not isinstance(custom_fields, dict)
            or len(custom_fields) > 10
            or any(
                not isinstance(key, str)
                or not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]{0,79}$", key)
                or not (value is None or isinstance(value, (str, bool, int, float)))
                or isinstance(value, (dict, list, tuple))
                or isinstance(value, str) and len(value) > 1000
                or isinstance(value, float) and not math.isfinite(value)
                for key, value in custom_fields.items()
            )
        ):
            raise ValueError("Condição de campo personalizado inválida; use até 10 valores escalares JSON.")
        if "due_set" in self.conditions and type(self.conditions["due_set"]) is not bool:
            raise ValueError("Condição de prazo exige verdadeiro/falso.")
        if "overdue" in self.conditions and type(self.conditions["overdue"]) is not bool:
            raise ValueError("Condição de atraso exige verdadeiro/falso.")
        for key in ("release_assigned", "component_assigned", "blocked"):
            if key in self.conditions and type(self.conditions[key]) is not bool:
                raise ValueError("Condições de release, componente e dependência exigem verdadeiro/falso.")
        due_window = self.conditions.get("due_within_days")
        if due_window is not None and (type(due_window) is not int or not 0 <= due_window <= 3650):
            raise ValueError("A janela de prazo deve estar entre 0 e 3.650 dias corridos.")
        for key in ("statuses", "work_types", "labels", "approval_states"):
            value = self.conditions.get(key, [])
            if (
                not isinstance(value, list)
                or len(value) > 30
                or any(not isinstance(item, str) or not 1 <= len(item) <= 80 for item in value)
            ):
                raise ValueError("Lista de condições inválida.")
        for key in ("development_providers", "development_event_types", "development_states"):
            value = self.conditions.get(key, [])
            if (
                not isinstance(value, list)
                or len(value) > 20
                or any(not isinstance(item, str) or not 1 <= len(item.strip()) <= 60 for item in value)
            ):
                raise ValueError("Filtro de evento de desenvolvimento inválido.")
        if set(self.conditions.get("development_providers", [])) - {"github", "gitlab", "bitbucket"}:
            raise ValueError("Provedor de desenvolvimento não suportado.")
        development_conditions = {
            "development_providers", "development_event_types", "development_states"
        }
        if development_conditions.intersection(self.conditions) and self.trigger != "development_event":
            raise ValueError("Filtros de SCM exigem o gatilho de evento de desenvolvimento.")
        if "comment_contains" in self.conditions:
            value = self.conditions["comment_contains"]
            if self.trigger != "comment_added" or not isinstance(value, str) or not 1 <= len(value.strip()) <= 200:
                raise ValueError("Trecho de comentário exige o gatilho de comentário e texto de até 200 caracteres.")
        if "attachment_media_types" in self.conditions:
            value = self.conditions["attachment_media_types"]
            if (
                self.trigger != "attachment_added"
                or not isinstance(value, list)
                or not 1 <= len(value) <= 4
                or any(not isinstance(item, str) for item in value)
                or len(value) != len(set(value))
                or set(value) - {"application/pdf", "image/png", "image/jpeg", "text/plain"}
            ):
                raise ValueError("Filtro de anexo exige tipos permitidos e o gatilho de anexo.")
        if "link_types" in self.conditions:
            value = self.conditions["link_types"]
            if (
                self.trigger not in {"link_added", "link_removed"}
                or not isinstance(value, list)
                or not 1 <= len(value) <= 3
                or len(value) != len(set(value))
                or set(value) - {"blocks", "relates", "duplicates"}
            ):
                raise ValueError("Filtro de relação exige o gatilho de relação e tipos permitidos.")
        if "changed_fields" in self.conditions:
            values = self.conditions["changed_fields"]
            allowed_fields = {
                "title", "description", "work_type", "parent_id", "labels",
                "priority", "due", "supplier_id", "assignee_user_id",
            }
            if (
                self.trigger != "field_changed"
                or not isinstance(values, list)
                or not 1 <= len(values) <= 20
                or any(not isinstance(value, str) for value in values)
                or len(values) != len(set(values))
                or any(
                    value not in allowed_fields
                    and not re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_]{0,79}$", value)
                    for value in values
                )
            ):
                raise ValueError("O gatilho de campo exige de 1 a 20 nomes válidos e sem repetição.")
        if "sprint_scope_actions" in self.conditions:
            values = self.conditions["sprint_scope_actions"]
            if (
                self.trigger != "sprint_scope_changed"
                or not isinstance(values, list)
                or not 1 <= len(values) <= 2
                or any(not isinstance(value, str) for value in values)
                or len(values) != len(set(values))
                or set(values) - {"added", "removed"}
            ):
                raise ValueError("A automação de escopo da sprint aceita ações adicionada/removida.")
        assignee_ids = self.conditions.get("assignee_user_ids", [])
        if (
            not isinstance(assignee_ids, list)
            or len(assignee_ids) > 30
            or any(type(identity) is not int or identity <= 0 for identity in assignee_ids)
            or len(assignee_ids) != len(set(assignee_ids))
        ):
            raise ValueError("Lista de responsáveis inválida.")
        if set(self.conditions.get("work_types", [])) - {"epic", "story", "task", "bug", "subtask"}:
            raise ValueError("Tipo de trabalho inválido na condição.")
        if set(self.conditions.get("approval_states", [])) - {"pending", "approved", "rejected", "resubmitted"}:
            raise ValueError("Estado de aprovação inválido na condição.")
        for key in ("priority_min", "priority_max"):
            value = self.conditions.get(key)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not -100000 <= value <= 100000
            ):
                raise ValueError("Prioridade da condição fora do limite.")
        if self.actions:
            self.action = self.actions[0].action
            self.config = self.actions[0].config
        elif self.action is not None:
            self.actions = [WorkflowAction(action=self.action, config=self.config)]
        else:
            raise ValueError("A automação precisa ter ao menos uma ação configurada.")
        return self


class DashboardWidgetInput(Input):
    name: str = Field(min_length=1, max_length=100)
    dashboard_id: StrictInt | None = Field(default=None, gt=0)
    jql: str = Field(default="", max_length=1000)
    group_by: Literal["status", "priority", "supplier", "sprint", "approval", "work_type", "assignee", "release", "component", "parent", "due_month", "created_month", "resolved_month", "overdue"]
    group_by_secondary: Literal["status", "priority", "supplier", "sprint", "approval", "work_type", "assignee", "release", "component", "parent", "due_month", "created_month", "resolved_month", "overdue"] | None = None
    measure: Literal["count", "estimated_minutes", "used_minutes", "remaining_minutes", "avg_open_age_days", "avg_resolution_days", "avg_current_status_days", "created_vs_resolved", "cost_cents"] = "count"
    chart: Literal["bar", "pie", "metric", "line", "matrix", "filter_results"] = "bar"
    result_columns: list[Literal["key", "summary", "status", "priority", "assignee", "supplier", "sprint", "due", "created_at", "work_type"]] = Field(default_factory=list, max_length=10)
    max_results: StrictInt = Field(default=50, ge=1, le=100)
    shared: bool = False
    shared_roles: list[Literal["admin", "manager", "internal"]] = Field(
        default_factory=list, max_length=3
    )
    shared_group_ids: list[StrictInt] = Field(default_factory=list, max_length=50)
    position: StrictInt = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def valid_sharing(self):
        self.jql = self.jql.strip()
        if self.shared and not (self.shared_roles or self.shared_group_ids):
            raise ValueError("Selecione ao menos um papel ou grupo para compartilhar o widget.")
        if not self.shared and (self.shared_roles or self.shared_group_ids):
            raise ValueError("Papéis e grupos exigem que o widget esteja compartilhado.")
        if any(identity <= 0 for identity in self.shared_group_ids) or len(set(self.shared_group_ids)) != len(self.shared_group_ids):
            raise ValueError("A lista de grupos compartilhados contém IDs inválidos ou repetidos.")
        if self.shared and re.search(r"\bfield_[a-zA-Z]|\btext\s*~", self.jql, re.IGNORECASE):
            raise ValueError("Widgets compartilhados não podem filtrar por valores personalizados ou texto em todos os campos.")
        if self.measure == "created_vs_resolved" and (
            self.group_by != "created_month" or self.chart != "line" or self.group_by_secondary is not None
        ):
            raise ValueError("O gráfico criados × concluídos usa mês de criação e visualização em linha.")
        if self.chart == "filter_results":
            if self.measure != "count" or self.group_by_secondary is not None:
                raise ValueError("A lista de resultados usa contagem e não cruza dimensões.")
            if len(self.result_columns) != len(set(self.result_columns)):
                raise ValueError("Não repita colunas na lista de resultados.")
            if not self.result_columns:
                self.result_columns = ["key", "summary", "status", "priority", "assignee", "due"]
        if self.group_by_secondary == self.group_by:
            raise ValueError("As duas dimensões do gadget precisam ser diferentes.")
        if self.chart == "matrix" and self.group_by_secondary is None:
            raise ValueError("A matriz exige a seleção de duas dimensões.")
        if self.group_by_secondary is not None and self.chart != "matrix":
            raise ValueError("A segunda dimensão exige apresentação em matriz.")
        return self


class DashboardInput(Input):
    name: str = Field(min_length=1, max_length=100)


class SavedViewOrder(Input):
    ids: list[StrictInt] = Field(max_length=100)


class DashboardWidgetOrderInput(Input):
    ids: list[StrictInt] = Field(max_length=100)
    dashboard_id: StrictInt | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def unique_ids(self):
        if any(identity <= 0 for identity in self.ids) or len(self.ids) != len(set(self.ids)):
            raise ValueError("A ordem contém IDs inválidos ou repetidos.")
        return self


class FilterSubscriptionInput(Input):
    name: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=1000)
    frequency: Literal["daily", "weekly"] = "daily"
    active: StrictBool = True

    @model_validator(mode="after")
    def query_is_not_blank(self):
        if not self.query.strip():
            raise ValueError("Informe uma consulta para a assinatura.")
        return self


class TaskScheduleInput(Version):
    planned_start: date | None = None
    due: date | None = None


class HoursInput(Version):
    estimated_minutes: StrictInt = Field(ge=0, le=600000)
    used_minutes: StrictInt = Field(ge=0, le=600000)
    comment: str = Field(default="", max_length=1000)


class Decision(Version):
    approved: bool
    hours_version: StrictInt = Field(gt=0)
    reason: str = Field(default="", max_length=1000)


class SprintInput(Input):
    name: str = Field(min_length=1, max_length=160)
    objective: str = Field(max_length=5000)
    starts: date
    ends: date


class SprintAction(Version):
    action: str
    reason: str = Field(default="", max_length=1000)


class AssignSprint(Version):
    task_id: StrictInt
    task_version: StrictInt


class FieldDefinition(Input):
    id: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,49}$")
    label: str = Field(min_length=1, max_length=100)
    type: str
    native_key: str | None = None
    options: list[str] = Field(default=[], max_length=100)
    required_for: list[str] = []
    visible_to: list[str] = ["admin", "manager", "internal", "supplier"]
    editable_by: list[str] = ["admin", "manager", "internal"]


class CardSchema(Version):
    fields: list[FieldDefinition] = Field(max_length=40)
    values: dict = Field(default_factory=dict)


class FieldValues(Version):
    values: dict


class SupplierCreate(SupplierInput):
    initial_rate_cents: StrictInt | None = Field(default=None, gt=0, le=100000000)


class ReorderItem(Input):
    id: StrictInt = Field(gt=0)
    version: StrictInt = Field(gt=0)
