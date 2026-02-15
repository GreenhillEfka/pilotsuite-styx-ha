"""Ops Runbook v0.1 - Operations runbook for OpenClaw Gateway."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

# Allowlist for safe commands (P1 Security Fix)
ALLOWED_COMMANDS = {
    "openclaw", "ls", "df", "du", "cat", "head", "tail", "grep", "find",
    "touch", "mkdir", "rm", "cp", "mv", "chmod", "chown",
    "git", "curl", "wget", "systemctl", "docker",
    "python3", "pip3", "node", "npm",
}

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .ops_runbook_store import (
    OpsRunbookStore,
    async_get_runbook_state,
    async_set_last_check,
)

_LOGGER = logging.getLogger(__name__)

RUNBOOK_CONFIG = {
    "checks": {
        "gateway_status": {"cmd": ["openclaw", "gateway", "status"]},
        "disk_space": {"cmd": ["df", "-h", "/config/.openclaw/workspace"]},
        "nodes_status": {"timeout": 30},
        "workspace_permissions": {"cmd": ["ls", "-la", "/config/.openclaw/workspace"]},
    },
    "actions": {
        "gateway_restart": {"cmd": ["openclaw", "gateway", "restart"]},
        "gateway_stop": {"cmd": ["openclaw", "gateway", "stop"]},
        "gateway_start": {"cmd": ["openclaw", "gateway", "start"]},
        "emergency_backup": {"timeout": 60},
    },
    "checklists": [
        "daily_check",
        "pre_update",
        "post_update", 
        "sev1_quick_actions",
    ],
}


async def async_setup_ops_runbook(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ops Runbook integration."""
    _LOGGER.info("Setting up Ops Runbook v0.1")

    # Register services
    await _register_services(hass)
    
    # Initialize store
    store = OpsRunbookStore(hass)
    hass.data.setdefault(DOMAIN, {})["ops_runbook_store"] = store
    
    return True


async def _register_services(hass: HomeAssistant) -> None:
    """Register Ops Runbook services."""
    
    async def service_run_preflight_check(call: ServiceCall) -> None:
        """Run the preflight check routine."""
        await async_run_preflight_check(hass)
    
    async def service_run_smoke_test(call: ServiceCall) -> None:
        """Run the smoke test routine."""
        await async_run_smoke_test(hass)
    
    async def service_execute_runbook_action(call: ServiceCall) -> None:
        """Execute a specific runbook action."""
        action = call.data.get("action")
        if not action:
            raise ValueError("Action parameter is required")
        await async_execute_runbook_action(hass, action)
    
    async def service_run_checklist(call: ServiceCall) -> None:
        """Run a specific checklist."""
        checklist = call.data.get("checklist")
        if not checklist:
            raise ValueError("Checklist parameter is required")
        await async_run_checklist(hass, checklist)

    # Register services
    hass.services.async_register(
        DOMAIN, "ops_runbook_preflight_check", service_run_preflight_check
    )
    hass.services.async_register(
        DOMAIN, "ops_runbook_smoke_test", service_run_smoke_test
    )
    hass.services.async_register(
        DOMAIN, "ops_runbook_execute_action", service_execute_runbook_action
    )
    hass.services.async_register(
        DOMAIN, "ops_runbook_run_checklist", service_run_checklist
    )


async def async_run_preflight_check(hass: HomeAssistant) -> dict[str, Any]:
    """Run the preflight check as per spec (1-2 minutes)."""
    _LOGGER.info("Running Ops Runbook preflight check")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "status": "pending",
        "duration_seconds": 0,
    }
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # 1. Gateway läuft?
        gateway_result = await _run_command(["openclaw", "gateway", "status"])
        results["checks"]["gateway_status"] = {
            "success": gateway_result["return_code"] == 0,
            "output": gateway_result["stdout"],
            "error": gateway_result["stderr"],
        }
        
        # 2. Workspace beschreibbar?
        workspace_result = await _run_command(["ls", "-la", "/config/.openclaw/workspace"])
        results["checks"]["workspace_accessible"] = {
            "success": workspace_result["return_code"] == 0,
            "output": workspace_result["stdout"],
            "error": workspace_result["stderr"],
        }
        
        # 3. Disk space
        disk_result = await _run_command(["df", "-h", "/config/.openclaw/workspace"])
        results["checks"]["disk_space"] = {
            "success": disk_result["return_code"] == 0,
            "output": disk_result["stdout"],
            "error": disk_result["stderr"],
        }
        
        # Determine overall status
        all_success = all(check.get("success", False) for check in results["checks"].values())
        results["status"] = "pass" if all_success else "fail"
        
    except Exception as e:
        _LOGGER.exception("Error during preflight check")
        results["status"] = "error"
        results["error"] = str(e)
    
    finally:
        end_time = datetime.now(timezone.utc)
        results["duration_seconds"] = (end_time - start_time).total_seconds()
    
    # Store result
    store = hass.data[DOMAIN].get("ops_runbook_store")
    if store:
        await store.async_store_check_result("preflight", results)
    
    # Send notification
    await _send_runbook_notification(hass, "Preflight Check", results)
    
    return results


async def async_run_smoke_test(hass: HomeAssistant) -> dict[str, Any]:
    """Run the smoke test as per spec (after update)."""
    _LOGGER.info("Running Ops Runbook smoke test")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "status": "pending",
        "duration_seconds": 0,
    }
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Gateway status
        gateway_result = await _run_command(["openclaw", "gateway", "status"])
        results["checks"]["gateway_status"] = {
            "success": gateway_result["return_code"] == 0,
            "output": gateway_result["stdout"],
            "error": gateway_result["stderr"],
        }
        
        # OpenClaw help (basic functionality test)
        help_result = await _run_command(["openclaw", "help"])
        results["checks"]["openclaw_help"] = {
            "success": help_result["return_code"] == 0,
            "output": help_result["stdout"][:200] + "..." if len(help_result["stdout"]) > 200 else help_result["stdout"],
            "error": help_result["stderr"],
        }
        
        # Check workspace write permissions
        test_file = "/config/.openclaw/workspace/.ops_runbook_test"
        write_test = await _run_command(["touch", test_file])
        cleanup_test = await _run_command(["rm", "-f", test_file])
        results["checks"]["workspace_writable"] = {
            "success": write_test["return_code"] == 0 and cleanup_test["return_code"] == 0,
            "output": "Write test completed",
            "error": write_test["stderr"] or cleanup_test["stderr"],
        }
        
        # Determine overall status
        all_success = all(check.get("success", False) for check in results["checks"].values())
        results["status"] = "pass" if all_success else "fail"
        
    except Exception as e:
        _LOGGER.exception("Error during smoke test")
        results["status"] = "error"
        results["error"] = str(e)
    
    finally:
        end_time = datetime.now(timezone.utc)
        results["duration_seconds"] = (end_time - start_time).total_seconds()
    
    # Store result
    store = hass.data[DOMAIN].get("ops_runbook_store")
    if store:
        await store.async_store_check_result("smoke_test", results)
    
    # Send notification
    await _send_runbook_notification(hass, "Smoke Test", results)
    
    return results


async def async_execute_runbook_action(hass: HomeAssistant, action: str) -> dict[str, Any]:
    """Execute a specific runbook action."""
    _LOGGER.info(f"Executing Ops Runbook action: {action}")
    
    if action not in RUNBOOK_CONFIG["actions"]:
        raise ValueError(f"Unknown action: {action}")
    
    action_config = RUNBOOK_CONFIG["actions"][action]
    result = {
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": False,
        "output": "",
        "error": "",
    }
    
    try:
        if "cmd" in action_config:
            cmd_result = await _run_command(action_config["cmd"])
            result["success"] = cmd_result["return_code"] == 0
            result["output"] = cmd_result["stdout"]
            result["error"] = cmd_result["stderr"]
        elif action == "emergency_backup":
            # Special handling for backup
            backup_result = await _create_emergency_backup(hass)
            result.update(backup_result)
        
    except Exception as e:
        _LOGGER.exception(f"Error executing action {action}")
        result["error"] = str(e)
    
    # Store result
    store = hass.data[DOMAIN].get("ops_runbook_store")
    if store:
        await store.async_store_action_result(action, result)
    
    return result


async def async_run_checklist(hass: HomeAssistant, checklist: str) -> dict[str, Any]:
    """Run a specific checklist."""
    _LOGGER.info(f"Running Ops Runbook checklist: {checklist}")
    
    if checklist not in RUNBOOK_CONFIG["checklists"]:
        raise ValueError(f"Unknown checklist: {checklist}")
    
    result = {
        "checklist": checklist,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "items": [],
        "status": "pending",
    }
    
    # Define checklist items based on spec
    checklist_items = _get_checklist_items(checklist)
    
    for item in checklist_items:
        item_result = {
            "description": item["description"],
            "status": "pending",
            "notes": "",
        }
        
        if item.get("auto_check"):
            # Automated check
            try:
                if item["check_type"] == "command":
                    cmd_result = await _run_command(item["command"])
                    item_result["status"] = "pass" if cmd_result["return_code"] == 0 else "fail"
                    item_result["notes"] = cmd_result["stdout"][:100] + "..." if len(cmd_result["stdout"]) > 100 else cmd_result["stdout"]
            except Exception as e:
                item_result["status"] = "error"
                item_result["notes"] = str(e)
        else:
            # Manual check - mark as pending for operator review
            item_result["status"] = "manual_review_required"
            item_result["notes"] = "Manual verification required"
        
        result["items"].append(item_result)
    
    # Determine overall checklist status
    statuses = [item["status"] for item in result["items"]]
    if all(status == "pass" for status in statuses):
        result["status"] = "complete"
    elif any(status == "error" for status in statuses):
        result["status"] = "error"
    elif any(status == "fail" for status in statuses):
        result["status"] = "failed"
    else:
        result["status"] = "review_required"
    
    # Store result
    store = hass.data[DOMAIN].get("ops_runbook_store")
    if store:
        await store.async_store_checklist_result(checklist, result)
    
    # Send notification
    await _send_runbook_notification(hass, f"Checklist: {checklist}", result)
    
    return result


async def _run_command(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    """Run a shell command with timeout (whitelist validated)."""
    # P1 Security: Validate command is in allowlist
    if cmd and cmd[0] not in ALLOWED_COMMANDS:
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command not allowed: {cmd[0]}. Use only: {', '.join(ALLOWED_COMMANDS)}",
        }
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
        
        return {
            "return_code": process.returncode,
            "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
            "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
        }
        
    except asyncio.TimeoutError:
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": str(e),
        }


async def _create_emergency_backup(hass: HomeAssistant) -> dict[str, Any]:
    """Create an emergency backup of critical files."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = f"/config/.openclaw/workspace/.ops_runbook_backup_{timestamp}"
    
    result = {
        "success": False,
        "backup_path": backup_dir,
        "output": "",
        "error": "",
    }
    
    try:
        # Create backup directory
        mkdir_result = await _run_command(["mkdir", "-p", backup_dir])
        if mkdir_result["return_code"] != 0:
            result["error"] = f"Failed to create backup directory: {mkdir_result['stderr']}"
            return result
        
        # Backup critical directories
        backup_paths = [
            "/config/.openclaw/workspace/docs",
            "/config/.openclaw/workspace/memory",
            "/config/.openclaw/workspace/notes",
            "/config/.openclaw/workspace/SOUL.md",
            "/config/.openclaw/workspace/USER.md",
            "/config/.openclaw/workspace/MEMORY.md",
            "/config/.openclaw/workspace/TOOLS.md",
        ]
        
        for path in backup_paths:
            copy_result = await _run_command(["cp", "-r", path, backup_dir])
            # Continue even if some files don't exist
        
        result["success"] = True
        result["output"] = f"Emergency backup created at {backup_dir}"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def _get_checklist_items(checklist: str) -> list[dict[str, Any]]:
    """Get checklist items based on the spec."""
    checklists = {
        "daily_check": [
            {
                "description": "openclaw gateway status is ok",
                "auto_check": True,
                "check_type": "command",
                "command": ["openclaw", "gateway", "status"],
            },
            {
                "description": "At least 1 Node online",
                "auto_check": False,  # Would need specific node checking logic
            },
            {
                "description": "1 kurzer Smoke-Test (z.B. notify oder browser snapshot)",
                "auto_check": False,  # Would need specific testing logic
            },
            {
                "description": "Disk space unkritisch",
                "auto_check": True,
                "check_type": "command",
                "command": ["df", "-h", "/config/.openclaw/workspace"],
            },
        ],
        "pre_update": [
            {
                "description": "Wartungsfenster kommuniziert",
                "auto_check": False,
            },
            {
                "description": "Backup/Commit gemacht",
                "auto_check": False,  # Could check git status
            },
            {
                "description": "Rollback-Pfad klar",
                "auto_check": False,
            },
            {
                "description": "Gateway stop (falls nötig)",
                "auto_check": False,
            },
        ],
        "post_update": [
            {
                "description": "Gateway läuft",
                "auto_check": True,
                "check_type": "command",
                "command": ["openclaw", "gateway", "status"],
            },
            {
                "description": "Browser test ok",
                "auto_check": False,  # Would need specific browser testing
            },
            {
                "description": "Nodes test ok",
                "auto_check": False,  # Would need specific node testing
            },
            {
                "description": "Messaging test ok (optional)",
                "auto_check": False,  # Would need specific messaging testing
            },
            {
                "description": "Change Log aktualisiert",
                "auto_check": False,
            },
        ],
        "sev1_quick_actions": [
            {
                "description": "Restart gateway",
                "auto_check": False,  # Action, not check
            },
            {
                "description": "Ressourcen prüfen (Disk/RAM)",
                "auto_check": True,
                "check_type": "command",
                "command": ["df", "-h"],
            },
            {
                "description": "Rollback wenn <10-15 min keine Stabilisierung",
                "auto_check": False,
            },
            {
                "description": "Status update an Stakeholder",
                "auto_check": False,
            },
        ],
    }
    
    return checklists.get(checklist, [])


async def _send_runbook_notification(hass: HomeAssistant, title: str, result: dict[str, Any]) -> None:
    """Send a notification about runbook results."""
    status = result.get("status", "unknown")
    
    if status == "pass" or status == "complete":
        notification_id = f"ops_runbook_success_{datetime.now().timestamp()}"
        message = f"✅ {title} completed successfully"
    elif status == "fail" or status == "failed" or status == "error":
        notification_id = f"ops_runbook_failure_{datetime.now().timestamp()}"
        message = f"❌ {title} failed - requires attention"
    else:
        notification_id = f"ops_runbook_pending_{datetime.now().timestamp()}"
        message = f"⚠️ {title} requires manual review"
    
    # Include key details
    if "duration_seconds" in result:
        message += f"\n⏱️ Duration: {result['duration_seconds']:.1f}s"
    
    if result.get("error"):
        message += f"\n🔍 Error: {result['error'][:100]}"
    
    persistent_notification.async_create(
        hass,
        message,
        title=f"Ops Runbook: {title}",
        notification_id=notification_id,
    )