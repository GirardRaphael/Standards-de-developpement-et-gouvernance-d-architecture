from dataclasses import dataclass, field
from enum import StrEnum


class PortalError(Exception):
    code = "ERREUR"


class Invalid(PortalError):
    code = "VALIDATION"


class Conflict(PortalError):
    code = "CONFLIT"


class Forbidden(PortalError):
    code = "ACCES_REFUSE"


class Missing(PortalError):
    code = "INTROUVABLE"


class Unavailable(PortalError):
    code = "INDISPONIBLE"


class Role(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    AGENT = "AGENT"
    SUPERVISOR = "SUPERVISOR"


class Status(StrEnum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Actor:
    id: str
    role: Role


def required(value: str, label: str, limit: int) -> str:
    if not isinstance(value, str):
        raise Invalid(f"{label} doit être un texte.")
    value = value.strip()
    if not value or len(value) > limit:
        raise Invalid(f"{label} doit contenir de 1 à {limit} caractères.")
    return value


def parse_status(value: str) -> Status:
    try:
        return Status(value)
    except ValueError:
        raise Invalid("État inconnu.") from None


@dataclass
class Request:
    id: str
    owner: str
    title: str
    description: str
    status: Status = Status.NEW
    assignee: str | None = None
    notes: list[dict[str, str]] = field(default_factory=list)

    def assign(self, assignee: str) -> None:
        if self.status not in {Status.NEW, Status.ASSIGNED}:
            raise Conflict("Affectation réservée aux demandes NEW ou ASSIGNED.")
        if self.assignee == assignee:
            raise Conflict("Cet agent est déjà affecté.")
        self.assignee = assignee
        self.status = Status.ASSIGNED

    def transition(self, target: Status) -> None:
        next_status = {
            Status.ASSIGNED: Status.IN_PROGRESS,
            Status.IN_PROGRESS: Status.RESOLVED,
            Status.RESOLVED: Status.CLOSED,
        }
        if next_status.get(self.status) != target:
            raise Conflict(f"Transition {self.status} → {target} interdite.")
        if target == Status.IN_PROGRESS and self.assignee is None:
            raise Conflict("Une affectation préalable est obligatoire.")
        self.status = target

    def add_note(self, author: str, note: str) -> None:
        if self.status == Status.CLOSED:
            raise Conflict("Une demande fermée est en lecture seule.")
        self.notes.append({"author": author, "text": note})
