from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from .domain import Request, Status


@dataclass(frozen=True)
class Receipt:
    fingerprint: str
    request_id: str
    status: str


class RequestRepository(Protocol):
    def get(self, request_id: str) -> Request | None: ...

    def list(self, owner: str | None, status: Status | None) -> list[Request]: ...

    def save(self, request: Request) -> None: ...

    def receipt(self, actor_id: str, key: str) -> Receipt | None: ...

    def record(self, actor_id: str, key: str, receipt: Receipt) -> None: ...


class Storage(Protocol):
    def transaction(
        self, *, write: bool = False
    ) -> AbstractContextManager[RequestRepository]: ...
