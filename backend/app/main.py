from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import VeriAgentError
from backend.app.services.hub import ServiceContainer
from veriagent_mcp.server import build_mcp_server


settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
container = ServiceContainer(settings)
mcp_server = build_mcp_server(container)
mcp_server.settings.streamable_http_path = "/"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = container
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(
    title="VeriAgent Backend",
    version="0.1.0",
    lifespan=lifespan,
    description="Shared backend for the VeriAgent dashboard and MCP integration.",
)
app.state.container = container

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(VeriAgentError)
async def handle_veriagent_error(_: Request, exc: VeriAgentError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {"code": "request_validation_error", "message": str(exc)}})


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "VeriAgent",
        "description": "Agentic AI-driven quality engineering hub.",
        "health": "/api/health",
        "mcp": settings.resolved_mcp_url(),
    }


app.include_router(router)
app.mount("/mcp", mcp_server.streamable_http_app())
