"""Tests for Alembic recovery when schema exists without alembic_version."""

from backend.db_migrate import (
    CORE_TABLES,
    EXTRA_TABLES,
    INITIAL_REVISION,
    _stamp_revision_for_existing_schema,
    _table_exists,
)


class FakeCursor:
    def __init__(self, tables: set[str], alembic_version: str | None = None) -> None:
        self.tables = tables
        self.alembic_version = alembic_version
        self.stamped: str | None = None

    def execute(self, query, params=()):
        self._last_query = query
        self._last_params = params

    def fetchone(self):
        if "alembic_version" in self._last_query:
            if self.alembic_version is None:
                return None
            return (self.alembic_version,)
        if "to_regclass" in self._last_query:
            name = self._last_params[0].removeprefix("public.")
            return (name,) if name in self.tables else (None,)
        return None


class FakeConfig:
    pass


def test_table_exists():
    cur = FakeCursor({"tickets"})
    assert _table_exists(cur, "tickets") is True
    assert _table_exists(cur, "sessions") is False


def test_stamp_skips_when_alembic_version_present(monkeypatch):
    cur = FakeCursor(set(CORE_TABLES) | {"alembic_version"}, alembic_version=INITIAL_REVISION)
    config = FakeConfig()

    def fake_stamp(_config, revision):
        raise AssertionError(f"stamp should not run, got {revision}")

    monkeypatch.setattr("alembic.command.stamp", fake_stamp)
    _stamp_revision_for_existing_schema(cur, config)


def test_stamp_initial_when_core_tables_exist(monkeypatch):
    cur = FakeCursor(set(CORE_TABLES))
    config = FakeConfig()
    stamped: list[str] = []

    def fake_stamp(_config, revision):
        stamped.append(revision)

    monkeypatch.setattr("alembic.command.stamp", fake_stamp)
    _stamp_revision_for_existing_schema(cur, config)
    assert stamped == [INITIAL_REVISION]


def test_stamp_head_when_all_tables_exist(monkeypatch):
    cur = FakeCursor(set(CORE_TABLES) | set(EXTRA_TABLES))
    config = FakeConfig()
    stamped: list[str] = []

    def fake_stamp(_config, revision):
        stamped.append(revision)

    monkeypatch.setattr("alembic.command.stamp", fake_stamp)
    _stamp_revision_for_existing_schema(cur, config)
    assert stamped == ["head"]
