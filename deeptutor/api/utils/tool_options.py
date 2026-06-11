"""Configurable-tool surface shared by the partners and multi-user admin APIs.

``tools`` mirrors the user-toggleable system tools (the same pool the chat
composer / settings expose); ``mcp_tools`` lists every configured MCP tool
that a whitelist (partner config or user grant) could allow.
"""

from __future__ import annotations

import logging
from typing import Any

from deeptutor.core.i18n import current_language
from deeptutor.core.metadata_i18n import localized_description, tool_description_i18n

logger = logging.getLogger(__name__)


async def build_tool_options() -> dict[str, list[dict[str, Any]]]:
    from deeptutor.agents._shared.tool_composition import default_optional_tools
    from deeptutor.runtime.registry.tool_registry import get_tool_registry

    registry = get_tool_registry()
    language = current_language()
    try:
        from deeptutor.services.mcp import get_mcp_manager

        await get_mcp_manager().ensure_started()
    except Exception:
        logger.debug("MCP manager unavailable for tool options", exc_info=True)

    tools: list[dict[str, Any]] = []
    for name in default_optional_tools():
        tool = registry.get(name)
        description = ""
        if tool is not None:
            try:
                description = tool.get_definition().description or ""
            except Exception:
                description = ""
        descriptions = tool_description_i18n(name, description)
        tools.append(
            {
                "name": name,
                "description": localized_description(descriptions, language),
                "description_i18n": descriptions,
            }
        )

    mcp_tools: list[dict[str, Any]] = []
    for tool in registry.deferred_tools():
        try:
            definition = tool.get_definition()
        except Exception:
            continue
        mcp_tools.append(
            {
                "name": definition.name,
                "server": str(getattr(tool, "server_name", "") or ""),
                "description": definition.description or "",
                "description_i18n": {
                    "en": definition.description or "",
                    "zh": definition.description or "",
                },
            }
        )

    return {"tools": tools, "mcp_tools": mcp_tools}


__all__ = ["build_tool_options"]
