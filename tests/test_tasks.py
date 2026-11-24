"""The fetch task starts git by absolute path, and fails clearly without it."""

import pytest

from src import tasks


def test_git_executable_is_absolute(monkeypatch):
    monkeypatch.setattr(tasks.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert tasks.git_executable() == "/usr/bin/git"


def test_missing_git_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(tasks.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="git is not installed"):
        tasks.git_executable()
