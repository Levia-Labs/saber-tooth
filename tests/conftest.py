import pytest


@pytest.fixture(autouse=True)
def no_title_lookup(monkeypatch):
    """No test reaches YouTube: the title lookup answers nothing unless a test sets it."""
    monkeypatch.setattr("saber_tooth.api.generate_api.video_title", lambda url: None)
