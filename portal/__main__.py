import argparse
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
import warnings
from pathlib import Path

from .domain import Actor, Forbidden, PortalError, Role, parse_status
from .service import Service
from .sqlite import SQLiteStorage


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def initialize(directory: Path, storage: SQLiteStorage) -> None:
    directory.mkdir(mode=0o700)
    storage.initialize()
    accounts = {}
    tokens = {}
    for name, role in (
        ("employe", Role.EMPLOYEE),
        ("employe2", Role.EMPLOYEE),
        ("agent", Role.AGENT),
        ("agent2", Role.AGENT),
        ("superviseur", Role.SUPERVISOR),
    ):
        token = secrets.token_urlsafe(32)
        accounts[name] = {"role": role, "digest": digest(token)}
        tokens[name] = token
    with (directory / "accounts.json").open("x", encoding="utf-8") as file:
        json.dump(accounts, file, indent=2)
    print("Jetons de démonstration affichés une seule fois.", file=sys.stderr)
    print(json.dumps(tokens, indent=2))


def authenticate(accounts: dict, name: str) -> Actor:
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        token = getpass.getpass("Jeton (saisie masquée) : ")
    account = accounts.get(name)
    expected = account["digest"] if account else "0" * 64
    if not hmac.compare_digest(expected, digest(token)) or account is None:
        raise Forbidden("Identifiants invalides.")
    return Actor(name, Role(account["role"]))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Portail local de demandes de service")
    root.add_argument("--instance", type=Path, default=Path("instance"))
    root.add_argument("--user", help="Identifiant du compte")
    actions = root.add_subparsers(dest="operation", required=True)
    actions.add_parser("init", help="Initialiser une instance de démonstration")
    actions.add_parser("get").add_argument("request_id")
    actions.add_parser("list").add_argument("--status")
    for operation in ("create", "assign", "status", "note"):
        command = actions.add_parser(operation)
        command.add_argument("--key", required=True)
        if operation != "create":
            command.add_argument("request_id")
        if operation == "assign":
            command.add_argument("assignee")
        if operation == "status":
            command.add_argument("status")
    return root


def execute(args: argparse.Namespace, service: Service, actor: Actor):
    operation = args.operation
    if operation == "list":
        return service.list(actor, parse_status(args.status) if args.status else None)
    if operation == "get":
        return service.get(actor, args.request_id)
    if operation == "create":
        fields = {"title": input("Titre : "), "description": input("Description : ")}
    else:
        fields = {"request_id": args.request_id}
        if operation == "assign":
            fields["assignee"] = args.assignee
        elif operation == "status":
            fields["status"] = args.status
        else:
            fields["text"] = input("Note interne : ")
    return service.command(actor, args.key, operation, **fields)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    storage = SQLiteStorage(args.instance / "requests.sqlite3")
    try:
        if args.operation == "init":
            previous_umask = os.umask(0o077)
            try:
                initialize(args.instance, storage)
            finally:
                os.umask(previous_umask)
            return 0
        with (args.instance / "accounts.json").open(encoding="utf-8") as file:
            accounts = json.load(file)
        actor = authenticate(accounts, args.user)
        service = Service(
            storage, {name: Role(data["role"]) for name, data in accounts.items()}
        )
        print("Traitement en cours…", file=sys.stderr)
        print(json.dumps(execute(args, service, actor), indent=2))
        return 0
    except PortalError as error:
        print(f"{error.code} — {error}", file=sys.stderr)
        return 1
    except getpass.GetPassWarning:
        print(
            "ACCES_REFUSE — Un terminal avec saisie masquée est requis.",
            file=sys.stderr,
        )
        return 1
    except (EOFError, KeyboardInterrupt):
        print("ANNULÉ — Si nécessaire, réessayez avec la même clé.", file=sys.stderr)
        return 1
    except FileExistsError:
        print("INSTANCE_EXISTANTE — Utilisez une autre instance.", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(
            "CONFIGURATION — Vérifiez les fichiers et droits de l’instance.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
