"""Structured events for the ELK monitoring layer.

Run: pytest -q tests/test_observability.py
"""

import json

from fastapi.testclient import TestClient

from src.app import app
from src.observability import churner_recall, emit, get_logger

CUSTOMER = {
    "CreditScore": 850,
    "Gender": 0,
    "Age": 43,
    "Tenure": 2,
    "Balance": 125510.82,
    "NumOfProducts": 1,
    "HasCrCard": 1,
    "IsActiveMember": 1,
    "EstimatedSalary": 79084.10,
}


def _events(text: str) -> list[dict]:
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def test_event_is_one_json_line(capsys):
    emit(get_logger("test"), "training_run", accuracy=0.8555, flow="all")
    (doc,) = _events(capsys.readouterr().out)
    assert doc["event"] == "training_run"
    assert doc["service"] == "test"
    assert doc["accuracy"] == 0.8555
    assert "@timestamp" in doc


def test_churner_recall_from_confusion_matrix():
    # The holdout matrix in the README: 176 of 415 churners caught.
    assert churner_recall([[1535, 50], [239, 176]]) == 0.4241


def test_predict_emits_request_and_prediction_events(capsys):
    assert TestClient(app).post("/predict", json=CUSTOMER).status_code == 200
    docs = _events(capsys.readouterr().out)
    kinds = {d["event"] for d in docs}
    assert {"prediction", "http_request"} <= kinds
    request = next(d for d in docs if d["event"] == "http_request")
    assert request["path"] == "/predict" and request["status"] == 200
    assert next(d for d in docs if d["event"] == "prediction")["exited"] == 0
