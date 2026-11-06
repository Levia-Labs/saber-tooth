import pytest


@pytest.fixture(autouse=True)
def no_title_lookup(monkeypatch):
    """No test reaches YouTube: the title lookup answers nothing unless a test sets it."""
    monkeypatch.setattr("saber_tooth.api.generate_api.video_title", lambda url: None)


@pytest.fixture(autouse=True)
def no_analyser_backoff(monkeypatch):
    """Retries of a failing fake analyser do not sleep; tests of the backoff pass their own."""
    monkeypatch.setattr("saber_tooth.analyser_client.BACKOFF_S", 0.0)
