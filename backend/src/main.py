import sentry_sdk
import taskiq_fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.broker import broker
from src.core.config import settings
from src.core.exceptions import BaseException
from src.core.handlers import global_exception_handler, local_exception_handler
from src.core.lifecycle import lifespan
from src.routes import (
    campaigns,
    contacts,
    dashboard,
    messages,
    tags,
    templates,
    waba,
    webhooks,
)

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        send_default_pii=True,
        enable_logs=True,
    )

app = FastAPI(lifespan=lifespan)

app.add_exception_handler(BaseException, local_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

taskiq_fastapi.init(broker, app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(contacts.router)
app.include_router(messages.router)
app.include_router(waba.router)
app.include_router(campaigns.router)
app.include_router(templates.router)
app.include_router(dashboard.router)
app.include_router(tags.router)
