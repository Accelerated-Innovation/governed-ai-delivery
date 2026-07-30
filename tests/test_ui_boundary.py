import json

import pytest

from cli.ui_boundary import scan_ui_boundary


def test_scans_packages_imports_sql_migrations_and_connection_keys(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "^16", "pg": "^8"}}),
        encoding="utf-8",
    )
    source = tmp_path / "src"
    source.mkdir()
    (source / "client.ts").write_text(
        "import postgres from 'postgres';\nconst key = { DATABASE_URL: 'redacted' };\n",
        encoding="utf-8",
    )
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001.sql").write_text("select 1;", encoding="utf-8")

    violations = scan_ui_boundary(tmp_path)
    rules = {violation.rule for violation in violations}

    assert {
        "database-package",
        "database-import",
        "connection-string",
        "database-artifact",
        "sql-file",
    } <= rules


def test_ignores_generated_and_dependency_directories(tmp_path):
    generated = tmp_path / "node_modules" / "pg"
    generated.mkdir(parents=True)
    (generated / "index.js").write_text("require('pg')", encoding="utf-8")

    assert scan_ui_boundary(tmp_path) == []


@pytest.mark.parametrize(
    "package",
    ["@prisma/client", "drizzle-orm", "pg", "mysql2", "mssql"],
)
def test_representative_database_dependencies_fail(tmp_path, package):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {package: "latest"}}),
        encoding="utf-8",
    )

    violations = scan_ui_boundary(tmp_path)

    assert any(
        violation.rule == "database-package" and package in violation.detail
        for violation in violations
    )


def test_server_action_and_route_handler_using_backend_api_pass(tmp_path):
    source = tmp_path / "src" / "app" / "api" / "orders"
    source.mkdir(parents=True)
    (source / "route.ts").write_text(
        "export async function GET() { return fetch('https://backend/orders'); }\n",
        encoding="utf-8",
    )
    action = tmp_path / "src" / "features" / "orders" / "application"
    action.mkdir(parents=True)
    (action / "create-order.ts").write_text(
        "'use server';\nexport const createOrder = () => fetch('https://backend/orders', {method:'POST'});\n",
        encoding="utf-8",
    )

    assert scan_ui_boundary(tmp_path) == []


def test_scan_is_target_scoped_and_ignores_sibling_backend(tmp_path):
    ui = tmp_path / "apps" / "web"
    ui.mkdir(parents=True)
    (ui / "package.json").write_text(
        '{"dependencies":{"next":"^16"}}',
        encoding="utf-8",
    )
    backend = tmp_path / "apps" / "api" / "migrations"
    backend.mkdir(parents=True)
    (backend / "001.sql").write_text("select 1;", encoding="utf-8")

    assert scan_ui_boundary(ui) == []
