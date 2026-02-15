"""
UniFi Neuron - Network Monitoring Module

Provides WAN status, client roaming, and traffic baselines
for AI Home CoPilot context awareness.
"""

__version__ = "0.1.0"

from .service import UniFiService
from .api import unifi_bp

__all__ = ["UniFiService", "unifi_bp"]
