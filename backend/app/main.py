import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import commission_rules, companies, drivers, orders, reports, vehicles
from app.core.config import get_settings

logger = logging.getLogger("app")

settings = get_settings()

app = FastAPI(title="Supply Transport API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.detail, "status_code": exc.status_code}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak the raw exception message or a stack trace to the client —
    # log it server-side (with traceback) and return the same standardized
    # error shape every other endpoint uses.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Terjadi kesalahan internal pada server.",
                "status_code": 500,
            }
        },
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}


API_V1_PREFIX = "/api/v1"
app.include_router(companies.router, prefix=API_V1_PREFIX)
app.include_router(drivers.router, prefix=API_V1_PREFIX)
app.include_router(orders.router, prefix=API_V1_PREFIX)
app.include_router(reports.router, prefix=API_V1_PREFIX)
app.include_router(commission_rules.router, prefix=API_V1_PREFIX)
app.include_router(vehicles.router, prefix=API_V1_PREFIX)
