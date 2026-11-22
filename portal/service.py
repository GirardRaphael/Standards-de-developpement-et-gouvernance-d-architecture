from dataclasses import asdict
from hashlib import sha256
from json import dumps
from uuid import uuid4

from .domain import (
    Actor,
    Conflict,
    Forbidden,
    Invalid,
    Missing,
    Request,
    Role,
    Status,
    parse_status,
    required,
)
from .ports import Receipt, RequestRepository, Storage


def find(repo: RequestRepository, request_id: str) -> Request:
    request = repo.get(request_id)
    if request is None:
        raise Missing("Demande introuvable.")
    return request


class Service:
    def __init__(self, storage: Storage, actors: dict[str, Role]):
        self.storage = storage
        self.actors = actors

    def get(self, actor: Actor, request_id: str) -> dict:
        with self.storage.transaction() as repo:
            request = find(repo, request_id)
            if actor.role == Role.EMPLOYEE and request.owner != actor.id:
                raise Missing("Demande introuvable.")
            result = asdict(request)
            if actor.role != Role.SUPERVISOR and not (
                actor.role == Role.AGENT and request.assignee == actor.id
            ):
                result.pop("notes")
            return result

    def list(self, actor: Actor, status: Status | None = None) -> list[dict]:
        owner = actor.id if actor.role == Role.EMPLOYEE else None
        with self.storage.transaction() as repo:
            return [
                {"id": request.id, "title": request.title, "status": request.status}
                for request in repo.list(owner, status)
            ]

    def command(self, actor: Actor, key: str, operation: str, **fields: str) -> dict:
        clean_fields = self.validate(operation, fields)
        key = required(key, "Clé d’idempotence", 128)
        fingerprint = sha256(
            dumps([operation, clean_fields], sort_keys=True).encode()
        ).hexdigest()

        with self.storage.transaction(write=True) as repo:
            request = None
            if operation != "create":
                if actor.role == Role.EMPLOYEE:
                    raise Forbidden("Action réservée au personnel de traitement.")
                request = find(repo, clean_fields["request_id"])
                if (
                    actor.role == Role.AGENT
                    and operation != "assign"
                    and request.assignee != actor.id
                ):
                    raise Forbidden("Action réservée à l’agent affecté.")
                if actor.role != Role.SUPERVISOR and (
                    clean_fields.get("status") == Status.CLOSED
                    or (
                        operation == "assign"
                        and (
                            clean_fields["assignee"] != actor.id
                            or request.assignee not in {None, actor.id}
                        )
                    )
                ):
                    raise Forbidden("Action réservée au superviseur.")

            previous = repo.receipt(actor.id, key)
            if previous is not None:
                if previous.fingerprint != fingerprint:
                    raise Conflict("Clé déjà utilisée pour une autre commande.")
                return self.result(previous, replayed=True)

            if request is None:
                request = Request(
                    uuid4().hex,
                    actor.id,
                    clean_fields["title"],
                    clean_fields["description"],
                )
            elif operation == "assign":
                assignee = clean_fields["assignee"]
                if self.actors.get(assignee) != Role.AGENT:
                    raise Invalid("L’affectation exige un agent connu.")
                request.assign(assignee)
            elif operation == "status":
                request.transition(Status(clean_fields["status"]))
            else:
                request.add_note(actor.id, clean_fields["text"])

            repo.save(request)
            receipt = Receipt(fingerprint, request.id, request.status)
            repo.record(actor.id, key, receipt)
            return self.result(receipt, replayed=False)

    @staticmethod
    def validate(operation: str, fields: dict[str, str]) -> dict[str, str]:
        limits = {
            "create": {"title": 120, "description": 4000},
            "assign": {"request_id": 64, "assignee": 64},
            "status": {"request_id": 64, "status": 16},
            "note": {"request_id": 64, "text": 2000},
        }
        if operation not in limits or fields.keys() != limits[operation].keys():
            raise Invalid("Commande ou champs invalides.")
        clean = {
            name: required(fields[name], name, limit)
            for name, limit in limits[operation].items()
        }
        if operation == "status":
            parse_status(clean["status"])
        return clean

    @staticmethod
    def result(receipt: Receipt, *, replayed: bool) -> dict:
        return {
            "request_id": receipt.request_id,
            "status": receipt.status,
            "replayed": replayed,
        }
