from typing import Literal
from datetime import date
from pydantic import BaseModel, Field, ConfigDict, StrictInt


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


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


class TaskInput(Input):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=10000)
    supplier_id: StrictInt | None = None
    due: date | None = None
    priority: StrictInt = 0


class TaskCreate(TaskInput):
    estimate_policy: Literal["absent", "optional", "required"] = "absent"


class TaskEdit(TaskInput):
    version: StrictInt = Field(gt=0)


class Move(Version):
    status: str
    priority: StrictInt = 0
    reason: str = Field(default="", max_length=1000)


class HoursInput(Version):
    estimated_minutes: StrictInt = Field(ge=0, le=600000)
    used_minutes: StrictInt = Field(ge=0, le=600000)


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
