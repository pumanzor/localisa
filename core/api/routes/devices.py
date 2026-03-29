"""Devices routes — IoT control via MQTT and plugins."""

import logging
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from config import settings

router = APIRouter()
log = logging.getLogger("localisa.devices")


class DeviceCommand(BaseModel):
    device_id: str
    action: str  # on, off, toggle, set
    value: Optional[str] = None


@router.get("/devices")
async def list_devices():
    """List configured IoT devices."""
    # TODO: Load from plugins/home config
    return {"devices": [], "source": "plugins/home"}


@router.post("/devices/command")
async def send_command(cmd: DeviceCommand):
    """Send a command to an IoT device."""
    # TODO: Route to appropriate plugin (MQTT, Tuya, Shelly, etc.)
    log.info(f"Device command: {cmd.device_id} → {cmd.action} ({cmd.value})")
    return {
        "status": "ok",
        "device_id": cmd.device_id,
        "action": cmd.action,
        "note": "Plugin routing not yet implemented",
    }


@router.get("/devices/{device_id}/status")
async def device_status(device_id: str):
    """Get current status of a device."""
    # TODO: Query from plugin
    return {"device_id": device_id, "status": "unknown", "note": "Plugin routing not yet implemented"}
