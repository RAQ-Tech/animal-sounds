"""Configuration behaviour.

LOG_LEVEL was previously read, displayed, and returned by /api/info while
controlling nothing at all. These tests are what keep it honest.
"""

import logging

import pytest

from conftest import main


@pytest.fixture(autouse=True)
def restore_logging():
    """_configure_logging mutates global logging state; put it back."""
    root_level = logging.getLogger().level
    app_level = main.app.logger.level
    yield
    logging.getLogger().setLevel(root_level)
    main.app.logger.setLevel(app_level)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
    ],
)
def test_log_level_is_actually_applied(monkeypatch, value, expected):
    monkeypatch.setattr(main, "LOG_LEVEL", value)
    assert main._configure_logging() == value
    assert main.app.logger.level == expected


def test_log_level_is_case_and_whitespace_tolerant(monkeypatch):
    monkeypatch.setattr(main, "LOG_LEVEL", "  DEBUG  ")
    assert main._configure_logging() == "debug"
    assert main.app.logger.level == logging.DEBUG


def test_unknown_log_level_falls_back_to_info(monkeypatch):
    """A typo must not stop the container from starting."""
    monkeypatch.setattr(main, "LOG_LEVEL", "verbose-ish")
    assert main._configure_logging() == "info"


def test_api_info_reports_the_effective_level(client):
    """Reporting a level that was not understood would be a lie."""
    reported = client.get("/api/info").get_json()["log_level"]
    assert reported == main.EFFECTIVE_LOG_LEVEL
    assert reported in main.LOG_LEVELS


def test_requests_are_access_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger=main.app.logger.name):
        client.get("/api/info")
    assert any("/api/info" in record.getMessage() for record in caplog.records), (
        "requests should be access logged"
    )


def test_health_is_not_access_logged(client, caplog):
    """The container healthcheck hits /health every 30s; logging it is noise."""
    with caplog.at_level(logging.INFO, logger=main.app.logger.name):
        client.get("/health")
    assert not any("/health" in record.getMessage() for record in caplog.records), (
        "/health must stay out of the access log"
    )
