"""Basic tests for the prediction API.

Run: pytest -q tests/test_app.py
"""

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.model_pipeline import predict_model

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

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_predict():
    res = client.post("/predict", json=CUSTOMER)
    assert res.status_code == 200
    assert res.json() == {"exited": 0}


def test_predict_bad_input():
    # Missing fields must give a clean 422, never a server crash.
    bad = {k: v for k, v in CUSTOMER.items() if k != "Balance"}
    assert client.post("/predict", json=bad).status_code == 422


def test_predict_model_needs_9_features():
    with pytest.raises(ValueError):
        predict_model([1.0] * 8)
