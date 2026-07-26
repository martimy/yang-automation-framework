"""
Local web app entry point.

Run from the repo root:
    pip install -r requirements.txt -r gui/backend/requirements.txt
    uvicorn gui.backend.main:app --reload

Serves the API under /api/* and the Vue frontend (gui/frontend/) at /.
"""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services import pipeline, schema

app = FastAPI(title="clab_yang_netconf_gnmi GUI")

# CORS is wide open for local dev (e.g. running the frontend off a separate
# dev server / port during development). Tighten or remove once the frontend
# is only ever served from this same process.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Devices / Intent stage
# ---------------------------------------------------------------------------

@app.get("/api/devices")
def list_devices():
    devices = pipeline.load_devices()
    return [_device_summary(d) for d in devices]


@app.get("/api/devices/{host}")
def get_device(host: str):
    try:
        device = pipeline.load_device(host)
    except KeyError:
        raise HTTPException(404, f"No device '{host}' in devices.yml")
    intents = pipeline.dehydrate_intents(device.get("intents", {}))
    return {
        "host": device["host"],
        "vendor": device["vendor"],
        "username": device.get("username"),
        "intents": intents,
        # Keys with no dataclass/translator behind them (e.g. a hand-added
        # "protocols.snmp" block) -- preserved on save, but never deployed.
        "warnings": pipeline.unrecognized_intent_keys(intents),
    }


class DeviceUpdate(BaseModel):
    host: str
    vendor: str
    username: str | None = None
    intents: dict = {}


@app.put("/api/devices/{host}")
def update_device(host: str, update: DeviceUpdate):
    raw = update.model_dump()
    warnings = pipeline.unrecognized_intent_keys(raw.get("intents", {}))
    try:
        hydrated = pipeline.hydrate_device(raw)
    except pipeline.ValidationError as exc:
        raise HTTPException(422, str(exc))

    try:
        pipeline.save_device(host, hydrated["intents"])
    except KeyError:
        raise HTTPException(404, f"No device '{host}' in devices.yml")

    return {"status": "saved", "warnings": warnings}


def _device_summary(device: dict) -> dict:
    intents = device.get("intents", {})
    protocols = intents.get("protocols", {})
    return {
        "host": device["host"],
        "vendor": device["vendor"],
        "counts": {
            "interfaces": len(intents.get("interfaces", [])),
            "network_instances": len(intents.get("network_instances", [])),
            "ospf": len(protocols.get("ospf", [])),
            "ntp": len(protocols.get("ntp", [])),
        },
    }


# ---------------------------------------------------------------------------
# Schema (drives the Intent form) / Orchestration stage (read-only)
# ---------------------------------------------------------------------------

@app.get("/api/schema/intents")
def intent_schema():
    return schema.full_intent_schema()


@app.get("/api/schema/vendors/{vendor}")
def vendor_schema(vendor: str):
    if vendor not in schema.known_vendors():
        raise HTTPException(404, f"Unknown vendor '{vendor}', expected one of {schema.known_vendors()}")
    return {
        "vendor": vendor,
        "supported_intent_categories": schema.supported_intent_categories(vendor),
    }


@app.get("/api/orchestration/{host}")
def orchestration_info(host: str):
    """Read-only view of the Orchestration stage: which orchestrator class
    applies and the fixed phase order it runs (see design note: there's one
    orchestrator per vendor today, so this stage isn't editable yet)."""
    try:
        device = pipeline.load_device(host)
    except KeyError:
        raise HTTPException(404, f"No device '{host}' in devices.yml")

    vendor = device["vendor"]
    orchestrator_cls = pipeline.ORCHESTRATORS[vendor]
    return {
        "host": host,
        "vendor": vendor,
        "orchestrator_class": orchestrator_cls.__name__,
        "phase_order": ["network_instances", "interfaces", "ospf", "ntp"],
        "editable": False,
    }


# ---------------------------------------------------------------------------
# Translation stage preview (side-effect-free)
# ---------------------------------------------------------------------------

@app.get("/api/pipeline/{host}/translate")
def translate_preview(host: str, transport: Literal["netconf", "gnmi"] = "netconf"):
    try:
        payload_format = pipeline.PAYLOAD_FORMAT_MAP[transport]
        return pipeline.preview_translation(host, payload_format=payload_format)
    except KeyError:
        raise HTTPException(404, f"No device '{host}' in devices.yml")


# ---------------------------------------------------------------------------
# Deploy (Transport stage -- the real thing)
# ---------------------------------------------------------------------------

class DeployRequest(BaseModel):
    host: str
    transport: Literal["netconf", "gnmi"] = "netconf"


@app.post("/api/deploy")
def deploy(req: DeployRequest):
    try:
        return pipeline.run_deployment(req.host, transport_kind=req.transport)
    except KeyError:
        raise HTTPException(404, f"No device '{req.host}' in devices.yml")


# ---------------------------------------------------------------------------
# Frontend (static)
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
