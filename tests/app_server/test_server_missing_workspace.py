"""A session whose folder a rename took away moves where the process runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from vibe.app_server._host import HostRequestHandler
from vibe.app_server._process_services import ProcessServices
from vibe.app_server._session_backend_port import SessionBackend, SessionBackendHost
from vibe.app_server.models import IdleSessionStatus, PublicSession, PublicSessionState
from vibe.app_server.protocol import (
    SessionReadParams,
    SessionReadResponse,
    SessionRelocateParams,
    SessionRelocateResponse,
)
from vibe.app_server.server import AppServer
from vibe.app_server.transport import memory_transport_pair
from vibe.core.config.harness_files import HarnessFilesManager

_SESSION_ID = "root"


class _RootBackend:
    """The attached session, as far as the check reads it."""

    def __init__(self, cwd: str | None) -> None:
        self.session_id = _SESSION_ID
        self._cwd = cwd

    async def read(self, params: SessionReadParams) -> SessionReadResponse:
        session = PublicSession(
            id=self.session_id,
            status=IdleSessionStatus(),
            created_at=1,
            updated_at=1,
            cwd=self._cwd,
        )
        return SessionReadResponse(
            state=PublicSessionState(event_id=0, session=session), last_event_id=0
        )


class _StartingBackend(_RootBackend):
    """The attached session, as far as a turn's dispatch reaches it."""

    class Started(Exception):
        pass

    async def start_turn(self, params: Any) -> Any:
        raise self.Started


class _RelocatingHost:
    """The optional relocate capability, recording what it was asked to move."""

    def __init__(self) -> None:
        self.moves: list[tuple[str, str]] = []

    async def relocate(
        self, params: SessionRelocateParams, attached: SessionBackend | None
    ) -> SessionRelocateResponse:
        self.moves.append((params.session_id, params.cwd))
        session = PublicSession(
            id=params.session_id,
            status=IdleSessionStatus(),
            created_at=1,
            updated_at=1,
            cwd=params.cwd,
        )
        return SessionRelocateResponse(
            state=PublicSessionState(event_id=1, session=session), last_event_id=1
        )


def _server(host: Any, process_services: ProcessServices) -> AppServer:
    _, server_transport = memory_transport_pair()
    return AppServer(
        server_transport,
        session_backend_host_factory=lambda _: cast(SessionBackendHost, host),
        host_handler=HostRequestHandler(
            HarnessFilesManager(sources=("user", "project")),
            org_config=process_services.org_config,
            worktrees=process_services.worktrees,
            experiments=process_services.experiments,
            model_catalog=process_services.model_catalog,
        ),
        oidc_tenants=process_services.oidc_tenants,
        platform_credential_lenders=process_services.platform_credential_lenders,
    )


@pytest.mark.asyncio
async def test_a_turn_moves_a_session_whose_folder_is_gone(
    tmp_path: Path, process_services: ProcessServices, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _RelocatingHost()
    server = _server(host, process_services)
    monkeypatch.setattr(server, "_flush_backend_events", AsyncMock())
    renamed = tmp_path / "renamed"
    renamed.mkdir()
    renamed.rmdir()

    await server._recover_missing_workspace(
        cast(SessionBackend, _RootBackend(str(renamed)))
    )

    assert host.moves == [(_SESSION_ID, str(Path.cwd()))]


@pytest.mark.asyncio
async def test_a_turn_leaves_a_session_in_a_folder_that_exists(
    tmp_path: Path, process_services: ProcessServices, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _RelocatingHost()
    server = _server(host, process_services)
    monkeypatch.setattr(server, "_flush_backend_events", AsyncMock())

    await server._recover_missing_workspace(
        cast(SessionBackend, _RootBackend(str(tmp_path)))
    )

    assert host.moves == []


@pytest.mark.asyncio
async def test_a_turn_is_dispatched_after_the_move(
    tmp_path: Path, process_services: ProcessServices, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _RelocatingHost()
    server = _server(host, process_services)
    monkeypatch.setattr(server, "_flush_backend_events", AsyncMock())
    gone = tmp_path / "gone"
    gone.mkdir()
    gone.rmdir()
    backend = _StartingBackend(str(gone))

    with pytest.raises(_StartingBackend.Started):
        await server._dispatch_backend_operation(
            cast(SessionBackend, backend),
            "turn/start",
            {"sessionId": _SESSION_ID, "message": [{"type": "text", "text": "hi"}]},
        )

    assert host.moves == [(_SESSION_ID, str(Path.cwd()))]


@pytest.mark.asyncio
async def test_a_backend_without_relocation_keeps_its_session(
    tmp_path: Path, process_services: ProcessServices, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = _server(object(), process_services)
    monkeypatch.setattr(server, "_flush_backend_events", AsyncMock())
    gone = tmp_path / "gone"
    gone.mkdir()
    gone.rmdir()

    await server._recover_missing_workspace(
        cast(SessionBackend, _RootBackend(str(gone)))
    )

    server._flush_backend_events.assert_not_awaited()
