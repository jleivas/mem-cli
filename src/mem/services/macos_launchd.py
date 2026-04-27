from __future__ import annotations

from .autostart import LAUNCH_AGENT_FILENAME
from .autostart import LAUNCH_AGENT_LABEL
from .autostart import autostart_installed as launch_agent_installed
from .autostart import autostart_path as launch_agent_path
from .autostart import build_autostart_payload as build_launch_agent_payload
from .autostart import install_autostart as install_launch_agent
from .autostart import is_supported_platform
from .autostart import remove_autostart as remove_launch_agent

__all__ = [
    "LAUNCH_AGENT_FILENAME",
    "LAUNCH_AGENT_LABEL",
    "build_launch_agent_payload",
    "install_launch_agent",
    "is_supported_platform",
    "launch_agent_installed",
    "launch_agent_path",
    "remove_launch_agent",
]
