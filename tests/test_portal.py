import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from portal.__main__ import digest, main
from portal.domain import (
    Actor,
    Conflict,
    Forbidden,
    Invalid,
    Missing,
    Role,
    Status,
    Unavailable,
)
from portal.service import Service
from portal.sqlite import SQLiteStorage


class PortalTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(directory)
        self.storage = SQLiteStorage(self.path / "requests.sqlite3")
        self.storage.initialize()
        self.employee = Actor("employe", Role.EMPLOYEE)
        self.agent = Actor("agent", Role.AGENT)
        self.other = Actor("agent2", Role.AGENT)
        self.supervisor = Actor("superviseur", Role.SUPERVISOR)
        accounts = (self.employee, self.agent, self.other, self.supervisor)
        self.service = Service(
            self.storage, {actor.id: actor.role for actor in accounts}
        )

    def create(self):
        return self.service.command(
            self.employee, "creation", "create", title="Accès", description="VPN"
        )

    def change(self, actor, key, operation, request_id, **fields):
        return self.service.command(
            actor, key, operation, request_id=request_id, **fields
        )

    def test_valid_creation_and_filter(self):
        result = self.create()
        self.assertEqual(result["status"], Status.NEW)
        self.assertEqual(
            self.service.get(self.employee, result["request_id"])["owner"], "employe"
        )
        self.assertEqual(len(self.service.list(self.employee, Status.NEW)), 1)
        self.assertEqual(self.service.list(self.employee, Status.ASSIGNED), [])

    def test_invalid_creation(self):
        for title, description in [(" ", "VPN"), ("Accès", " "), ("a" * 121, "VPN")]:
            with (
                self.subTest(title=title, description=description),
                self.assertRaises(Invalid),
            ):
                self.service.command(
                    self.employee,
                    "creation",
                    "create",
                    title=title,
                    description=description,
                )
        self.assertEqual(self.service.list(self.employee), [])

    def test_invalid_transition_and_missing_assignment(self):
        identifier = self.create()["request_id"]
        for status in (Status.IN_PROGRESS, Status.CLOSED):
            with self.subTest(status=status), self.assertRaises(Conflict):
                self.change(
                    self.supervisor, "status", "status", identifier, status=status
                )
        self.assertEqual(
            self.service.get(self.employee, identifier)["status"], Status.NEW
        )

    def test_lifecycle_and_agent_cannot_close(self):
        identifier = self.create()["request_id"]
        self.change(self.agent, "take", "assign", identifier, assignee=self.agent.id)
        self.change(
            self.agent, "start", "status", identifier, status=Status.IN_PROGRESS
        )
        self.change(self.agent, "resolve", "status", identifier, status=Status.RESOLVED)
        with self.assertRaises(Forbidden):
            self.change(self.agent, "close", "status", identifier, status=Status.CLOSED)
        self.change(
            self.supervisor, "close", "status", identifier, status=Status.CLOSED
        )
        with self.assertRaises(Conflict):
            self.change(self.agent, "note", "note", identifier, text="Trop tard")
        self.assertEqual(
            self.service.get(self.employee, identifier)["status"], Status.CLOSED
        )

    def test_visibility_and_missing_request(self):
        identifier = self.create()["request_id"]
        employee2 = Actor("employe2", Role.EMPLOYEE)
        for missing in ("absent", identifier):
            with self.assertRaises(Missing):
                self.service.get(employee2, missing)
        self.assertEqual(self.service.list(employee2), [])
        with self.assertRaises(Forbidden):
            self.change(
                self.employee, "take", "assign", identifier, assignee=self.agent.id
            )
        self.change(self.agent, "take", "assign", identifier, assignee=self.agent.id)
        self.change(self.agent, "note", "note", identifier, text="Interne")
        with self.assertRaises(Forbidden):
            self.change(self.other, "note", "note", identifier, text="Interne")
        for actor in (self.employee, self.other):
            self.assertNotIn("notes", self.service.get(actor, identifier))
        for actor in (self.agent, self.supervisor):
            self.assertEqual(len(self.service.get(actor, identifier)["notes"]), 1)

    def test_concurrent_duplicate_and_key_conflict(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(lambda _: self.create(), range(2)))
        self.assertEqual(first["request_id"], second["request_id"])
        self.assertEqual({first["replayed"], second["replayed"]}, {False, True})
        self.assertEqual(len(self.service.list(self.employee)), 1)
        with self.assertRaises(Conflict):
            self.service.command(
                self.employee, "creation", "create", title="Autre", description="VPN"
            )

    def test_note_retry_has_one_effect(self):
        identifier = self.create()["request_id"]
        self.change(self.agent, "take", "assign", identifier, assignee=self.agent.id)
        for replayed in (False, True):
            result = self.change(self.agent, "note", "note", identifier, text="Interne")
            self.assertEqual(result["replayed"], replayed)
        self.assertEqual(len(self.service.get(self.agent, identifier)["notes"]), 1)

    def test_failed_receipt_rolls_back_request_and_allows_retry(self):
        with contextlib.closing(sqlite3.connect(self.storage.path)) as db, db:
            db.execute(
                "CREATE TRIGGER simulated_error BEFORE INSERT ON receipts "
                "BEGIN SELECT RAISE(ABORT, 'test'); END"
            )
        with self.assertRaises(Unavailable):
            self.create()
        self.assertEqual(self.service.list(self.employee), [])
        with contextlib.closing(sqlite3.connect(self.storage.path)) as db, db:
            db.execute("DROP TRIGGER simulated_error")
        self.assertFalse(self.create()["replayed"])

    def write_employee_account(self, token):
        accounts = {"employe": {"role": "EMPLOYEE", "digest": digest(token)}}
        (self.path / "accounts.json").write_text(json.dumps(accounts), encoding="utf-8")

    def test_cli_displays_failure_without_internal_details(self):
        self.write_employee_account("test")
        self.storage.path.unlink()
        error = io.StringIO()
        with patch("portal.__main__.getpass.getpass", return_value="test"):
            with contextlib.redirect_stderr(error):
                code = main(["--instance", str(self.path), "--user", "employe", "list"])
        self.assertEqual(code, 1)
        self.assertIn("Traitement en cours", error.getvalue())
        self.assertIn("INDISPONIBLE", error.getvalue())
        self.assertNotIn("no such table", error.getvalue())

    def test_cli_rejects_wrong_token(self):
        self.write_employee_account("right")
        error = io.StringIO()
        with patch("portal.__main__.getpass.getpass", return_value="wrong"):
            with contextlib.redirect_stderr(error):
                code = main(["--instance", str(self.path), "--user", "employe", "list"])
        self.assertEqual(code, 1)
        self.assertIn("ACCES_REFUSE", error.getvalue())

    def test_reassignment_revokes_old_agent_note_and_replay_access(self):
        identifier = self.create()["request_id"]
        self.change(self.agent, "take", "assign", identifier, assignee=self.agent.id)
        self.change(self.agent, "note", "note", identifier, text="Interne")
        self.change(
            self.supervisor, "transfer", "assign", identifier, assignee=self.other.id
        )

        self.assertNotIn("notes", self.service.get(self.agent, identifier))
        self.assertEqual(len(self.service.get(self.other, identifier)["notes"]), 1)
        with self.assertRaises(Forbidden):
            self.change(self.agent, "note", "note", identifier, text="Interne")
        with self.assertRaises(Forbidden):
            self.change(
                self.agent, "take", "assign", identifier, assignee=self.agent.id
            )

    def test_lock_refuses_write_and_allows_same_key_after_release(self):
        with contextlib.closing(sqlite3.connect(self.storage.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            with self.assertRaises(Unavailable):
                self.create()
            self.assertEqual(self.service.list(self.employee), [])
        result = self.create()
        self.assertFalse(result["replayed"])
        self.assertEqual(len(self.service.list(self.employee)), 1)

    def test_corrupted_row_reports_storage_failure(self):
        identifier = self.create()["request_id"]
        with contextlib.closing(sqlite3.connect(self.storage.path)) as db, db:
            db.execute(
                "UPDATE requests SET body = ? WHERE id = ?", ("{invalid", identifier)
            )
        with self.assertRaises(Unavailable):
            self.service.get(self.employee, identifier)

    def test_cli_create_writes_only_json_to_stdout(self):
        self.write_employee_account("test")
        output, error = io.StringIO(), io.StringIO()
        with (
            patch("portal.__main__.getpass.getpass", return_value="test"),
            patch("sys.stdin", io.StringIO("VPN\nDemande de connexion\n")),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(error),
        ):
            code = main(
                [
                    "--instance",
                    str(self.path),
                    "--user",
                    "employe",
                    "create",
                    "--key",
                    "vpn",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "NEW")
        self.assertIn("Titre", error.getvalue())

    def test_cli_rejects_explicit_empty_filter(self):
        self.write_employee_account("test")
        error = io.StringIO()
        with (
            patch("portal.__main__.getpass.getpass", return_value="test"),
            contextlib.redirect_stderr(error),
        ):
            code = main(
                [
                    "--instance",
                    str(self.path),
                    "--user",
                    "employe",
                    "list",
                    "--status",
                    "",
                ]
            )
        self.assertEqual(code, 1)
        self.assertIn("VALIDATION", error.getvalue())

    def test_cli_requires_user_before_requesting_token(self):
        with (
            patch("portal.__main__.getpass.getpass") as getpass,
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as failure,
        ):
            main(["list"])
        getpass.assert_not_called()
        self.assertEqual(failure.exception.code, 2)
