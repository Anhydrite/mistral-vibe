"""MCP and connector groups follow the Session's programmatic tool calling.

The route snapshots they come from are Host-level, so one Session's resolve can
outlive it into another Session's capabilities. Core refuses a capability set
that names a programmatic-only tool while programmatic tool calling is off, so a
Session without `run_typescript` -- the PicoVibe agent profile, for one -- must not
receive them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from mistralai_vibe_local_harness.protocol import (
    RustHarnessCapabilitySet,
    RustHarnessConfig,
    RustToolGroupDefinition,
)
from mistralai_vibe_local_harness.session_api.app_server.session.models import (
    TextContentBlock,
)
from mistralai_vibe_local_harness.session_api.app_server.session.procedures import (
    TurnStartParams,
    TurnStartResponse,
)
from mistralai_vibe_local_harness.session_protocol import (
    CompletedPublicTurn,
    SessionReadParams as RuntimeReadParams,
    SessionStartParams,
)
from mistralai_vibe_local_harness.vibe import UnifiedHarnessSessionBackendHost
from mistralai_vibe_local_harness.vibe._connector_models import (
    ConnectorRouteSnapshot,
    ConnectorToolDescriptor,
    ConnectorToolGroup,
    ResolvedConnector,
    ResolvedConnectorCatalog,
    ResolvedConnectorSelection,
    ResolvedConnectorTool,
)
from mistralai_vibe_local_harness.vibe._host import (
    _core_config,
    _integration_capability_update,
    _merge_integration_capabilities,
)
from mistralai_vibe_local_harness.vibe._runtime import DurableSessionRuntime
from mistralai_vibe_local_harness.vibe._runtime_config import LocalRuntimeAdapterConfig
from mistralai_vibe_local_harness.vibe._session_api_transport import (
    LocalSessionApiTransport,
    session_api_view_of,
)
from tests.app_server._session_api_harness import use_model_calling_one_tool

_BASE = RustHarnessCapabilitySet(
    tool_groups=[
        RustToolGroupDefinition(
            name="ui", tools=[{"name": "ask_user_question", "exposure": "direct"}]
        )
    ]
)

_CONNECTORS = ConnectorRouteSnapshot(
    catalog_revision="catalog-1",
    selection_revision="selection-1",
    route_revision="routes-1",
    groups=(
        ConnectorToolGroup(
            name="connector_web_search",
            description="Web search",
            tools=(
                ConnectorToolDescriptor(
                    raw_connector_id="web_search",
                    alias="web_search",
                    remote_name="finance_search",
                    group_name="connector_web_search",
                    programmatic_name="finance_search",
                    display_name="Finance search",
                    description="Search financial data",
                    input_schema={"type": "object"},
                    enabled=True,
                ),
            ),
        ),
    ),
    routes={},
    sources=(),
)


def _group_names(capabilities: RustHarnessCapabilitySet) -> list[str]:
    return [group.name for group in capabilities.tool_groups]


def test_a_session_with_programmatic_calling_gets_the_connector_groups() -> None:
    merged = _merge_integration_capabilities(
        _BASE,
        offers_programmatic_tools=True,
        mcp_snapshot=None,
        connector_snapshot=_CONNECTORS,
    )

    assert _group_names(merged) == ["ui", "connector_web_search"]


def test_a_session_without_programmatic_calling_keeps_its_own_groups_only() -> None:
    merged = _merge_integration_capabilities(
        _BASE,
        offers_programmatic_tools=False,
        mcp_snapshot=None,
        connector_snapshot=_CONNECTORS,
    )

    assert _group_names(merged) == ["ui"]


def test_a_connector_snapshot_landing_later_adds_nothing_without_programmatic() -> None:
    update = _integration_capability_update(
        _BASE,
        offers_programmatic_tools=lambda: False,
        mcp_snapshot=lambda: None,
        connector_snapshot=lambda: _CONNECTORS,
    )
    live = _BASE.model_copy(deep=True)

    assert update(live) is live


def test_a_connector_snapshot_landing_later_adds_the_groups_with_programmatic() -> None:
    update = _integration_capability_update(
        _BASE,
        offers_programmatic_tools=lambda: True,
        mcp_snapshot=lambda: None,
        connector_snapshot=lambda: _CONNECTORS,
    )

    assert _group_names(update(_BASE)) == ["ui", "connector_web_search"]


class _FakeGateway:
    """A connector gateway these tests never call."""

    async def call(
        self, *, raw_connector_id: str, remote_tool_name: str, arguments: object
    ) -> object:
        raise AssertionError("no connector tool should be callable here")

    async def aclose(self) -> None:
        return None


_CATALOG = ResolvedConnectorCatalog(
    revision="catalog-1",
    connectors=(
        ResolvedConnector(
            raw_id="web_search",
            alias="web_search",
            display_name="Web search",
            ready=True,
            auth_action="none",
            tools=(
                ResolvedConnectorTool(
                    raw_name="finance_search",
                    description="Search financial data",
                    input_schema={"type": "object"},
                ),
            ),
        ),
    ),
)
_SELECTION = ResolvedConnectorSelection(
    selection_revision="selection-1",
    enable_connectors=True,
    implicit_source_enabled=True,
    connector_settings=(),
    enabled_tools=(),
    disabled_tools=(),
)


def _config_without_programmatic_tools() -> RustHarnessConfig:
    config = _core_config("runtime-template")
    programmatic = config.settings.tools.programmatic.model_copy(
        update={"mode": "disabled", "sleep": "disabled"}
    )
    tools = config.settings.tools.model_copy(update={"programmatic": programmatic})
    return config.model_copy(
        update={"settings": config.settings.model_copy(update={"tools": tools})},
        deep=True,
    )


@pytest.mark.asyncio
async def test_a_session_without_programmatic_calling_still_starts_a_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """*Prepare*: A Session turns programmatic tool calling off while the Host has
    connectors resolved from another Session.
    *Do*: Start its first Turn.
    *Assert*: The Turn runs, and the connector groups stayed out of its catalog.
    """
    use_model_calling_one_tool(monkeypatch)
    host = UnifiedHarnessSessionBackendHost(tmp_path)
    host.configure_runtime(
        _config_without_programmatic_tools(),
        LocalRuntimeAdapterConfig.at(cwd=tmp_path, session_api=True),
    )
    host.configure_connectors(_CATALOG, _SELECTION, lambda: cast(Any, _FakeGateway()))
    session = await host.start(SessionStartParams(history_limit=50))
    transport = LocalSessionApiTransport(session, session_api_view_of(session))
    await transport.open()

    await transport.request(
        "app_server/session/turn/start",
        TurnStartParams(
            session_id=session.session_id, message=[TextContentBlock(text="Read a")]
        ),
        TurnStartResponse,
    )
    await session._wait_for_pending_turns()

    promoted = await session.read(
        RuntimeReadParams(session_id=session.session_id, history_limit=50)
    )
    assert isinstance(promoted.snapshot.state.latest_turn, CompletedPublicTurn)
    groups = [
        group.name
        for group in cast(
            DurableSessionRuntime, session._runtime
        ).config.capabilities.tool_groups
    ]
    assert "connector_web_search" not in groups
    await transport.close()
    await host.shutdown()
