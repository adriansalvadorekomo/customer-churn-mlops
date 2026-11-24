"""Simple prediction API.

Run: uv run uvicorn src.app:app --reload
Docs: http://127.0.0.1:8000/docs
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.model_pipeline import FEATURE_COLS, load_model, predict_model
from src.observability import Timer, emit, get_logger

app = FastAPI(title="Customer Churn MLOps")

# Browser frontends (Astro dashboard) call this API cross-origin — without
# CORS the browser blocks every request. Origins come from env so Docker
# (frontend service) and local dev (astro dev server) both work:
#   CORS_ORIGINS=http://localhost:4321,http://localhost:80
_cors_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:4321,http://localhost:80"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = load_model()
events = get_logger("api")


@app.middleware("http")
async def log_requests(request, call_next):
    """One ``http_request`` event per call (shipped to Elasticsearch in the monitoring profile)."""
    with Timer() as t:
        response = await call_next(request)
    emit(
        events,
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(t.seconds * 1000, 2),
    )
    return response


class Customer(BaseModel):
    CreditScore: float
    Gender: int
    Age: float
    Tenure: float
    Balance: float
    NumOfProducts: float
    HasCrCard: int
    IsActiveMember: int
    EstimatedSalary: float


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict")
def predict(customer: Customer) -> dict:
    features = [getattr(customer, col) for col in FEATURE_COLS]
    exited = predict_model(features, model=model)
    emit(events, "prediction", exited=int(exited))
    return {"exited": exited}
