"""Example unit tests for the churn pipeline (Étape 04.4).

Run:  ``pytest -q``  (also executed by the ``run-unit-tests`` Prefect task).
"""

from pathlib import Path

import pytest

from src.model_pipeline import (
    DEFAULT_DATA_PATH,
    evaluate_model,
    install_dependencies,
    load_model,
    prepare_data,
    save_model,
    train_model,
)


def test_prepare_data_shapes():
    """prepare_data returns the notebook's 8000/2000 split with 9 features."""
    X_train, X_test, y_train, y_test = prepare_data()
    assert X_train.shape == (8000, 9)
    assert X_test.shape == (2000, 9)
    assert len(y_train) == 8000
    assert len(y_test) == 2000


def test_train_evaluate_small():
    """A tiny forest still trains and scores in [0, 1]."""
    X_train, X_test, y_train, y_test = prepare_data()
    model = train_model(X_train, y_train, n_estimators=10)
    metrics = evaluate_model(model, X_test, y_test)
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["accuracy"] > 0.80
    assert metrics["confusion_matrix"].shape == (2, 2)


def test_save_load_roundtrip(tmp_path: Path):
    """save_model + load_model preserves predictions."""
    X_train, X_test, y_train, _ = prepare_data()
    model = train_model(X_train, y_train, n_estimators=10)
    path = tmp_path / "model.joblib"
    save_model(model, path)
    assert path.is_file()
    reloaded = load_model(path)
    assert list(reloaded.predict(X_test[:5])) == list(model.predict(X_test[:5]))


def test_install_dependencies_missing_file():
    """install_dependencies fails fast with a clear error on bad path."""
    with pytest.raises(FileNotFoundError):
        install_dependencies("does_not_exist_requirements.txt")


def test_load_model_missing_file(tmp_path: Path):
    """load_model fails fast with a clear error on bad path."""
    with pytest.raises(FileNotFoundError):
        load_model(tmp_path / "nope.joblib")


def test_default_dataset_exists():
    """The default CSV path must resolve (guards path regressions)."""
    assert Path(DEFAULT_DATA_PATH).is_file()
