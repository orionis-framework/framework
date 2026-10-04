"""Expose only the isolated diagnostic application registrations."""

from orionis.support.facades.mcp import Mcp
from tests.mcp.conformance.server import ConformanceServer

Mcp.web("/mcp", ConformanceServer)
Mcp.local("conformance", ConformanceServer)
