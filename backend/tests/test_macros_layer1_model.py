"""
CAMADA 1: Model + Schema + Seed
Testa integridade dos dados sem precisar de DB.
"""
import pytest
import json


# ── 1.1 Model structure (source analysis — avoids SQLAlchemy import issues on Python 3.14) ──

def _read_macro_model():
    with open("backend/app/models/macro.py") as f:
        return f.read()


def test_macro_model_has_use_count():
    src = _read_macro_model()
    assert "use_count" in src
    assert "Mapped[int]" in src
    assert "default=0" in src


def test_macro_model_has_created_by():
    src = _read_macro_model()
    assert "created_by" in src
    assert "Mapped[Optional[str]]" in src
    assert "String(255)" in src


def test_macro_model_has_actions_json():
    src = _read_macro_model()
    assert "actions" in src
    assert "JSON" in src
    assert "nullable=True" in src


def test_macro_model_imports_integer():
    src = _read_macro_model()
    assert "Integer" in src, "Model deve importar Integer pra use_count"


def test_macro_model_table_name():
    src = _read_macro_model()
    assert '__tablename__ = "macros"' in src


# ── 1.2 Schema validation ──

def test_macro_create_schema_basic():
    from app.schemas.kb import MacroCreate
    m = MacroCreate(name="Test", content="Hello", category="garantia")
    assert m.name == "Test"
    assert m.category == "garantia"
    assert m.actions is None


def test_macro_create_schema_with_actions():
    from app.schemas.kb import MacroCreate, MacroAction
    actions = [MacroAction(type="set_status", value="resolved")]
    m = MacroCreate(name="Test", content="Hello", actions=actions)
    assert len(m.actions) == 1
    assert m.actions[0].type == "set_status"


def test_macro_response_schema_has_use_count():
    from app.schemas.kb import MacroResponse
    data = {
        "id": "abc-123",
        "name": "Test",
        "content": "Hello",
        "is_active": True,
        "use_count": 42,
        "created_by": "Pedro",
    }
    r = MacroResponse(**data)
    assert r.use_count == 42
    assert r.created_by == "Pedro"


def test_macro_response_schema_use_count_defaults_zero():
    from app.schemas.kb import MacroResponse
    data = {
        "id": "abc-123",
        "name": "Test",
        "content": "Hello",
        "is_active": True,
    }
    r = MacroResponse(**data)
    assert r.use_count == 0
    assert r.created_by is None


def test_macro_update_schema_partial():
    from app.schemas.kb import MacroUpdate
    m = MacroUpdate(name="Updated")
    dumped = m.model_dump(exclude_unset=True)
    assert "name" in dumped
    assert "content" not in dumped
    assert "actions" not in dumped


def test_macro_action_schema_types():
    from app.schemas.kb import MacroAction
    valid_types = ["set_status", "set_priority", "add_tag", "set_category", "assign_to"]
    for t in valid_types:
        a = MacroAction(type=t, value="test")
        assert a.type == t


# ── 1.3 Seed data integrity ──

def test_seed_macros_count():
    """Seed deve ter pelo menos 20 macros."""
    import ast
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    # Count Macro( occurrences in the macros section
    count = src.count("Macro(name=")
    assert count >= 20, f"Seed tem apenas {count} macros, esperado >= 20"


def test_seed_macros_categories_aligned():
    """Todas as categorias do seed devem ser das 6 do sistema."""
    valid = {"meu_pedido", "garantia", "reenvio", "financeiro", "duvida", "reclamacao"}
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    cats = re.findall(r'category="(\w+)"', src)
    # Filter only macro categories (after "# ── Macros" section)
    macro_section = src[src.index("# ── Macros"):]
    macro_cats = re.findall(r'category="(\w+)"', macro_section)
    invalid = [c for c in macro_cats if c not in valid]
    assert not invalid, f"Categorias invalidas no seed: {invalid}"


def test_seed_macros_no_old_categories():
    """Nao pode ter categorias antigas (geral, troca, rastreamento)."""
    old_cats = {"geral", "troca", "rastreamento"}
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    macro_section = src[src.index("# ── Macros"):]
    macro_cats = set(re.findall(r'category="(\w+)"', macro_section))
    overlap = macro_cats & old_cats
    assert not overlap, f"Categorias antigas ainda presentes: {overlap}"


def test_seed_macros_use_valid_variables():
    """Macros do seed so devem usar variaveis validas."""
    valid_vars = {"cliente", "agente", "email", "numero", "assunto", "rastreio", "categoria", "prioridade", "status"}
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    macro_section = src[src.index("# ── Macros"):]
    used_vars = set(re.findall(r'\{\{(\w+)\}\}', macro_section))
    invalid = used_vars - valid_vars
    assert not invalid, f"Variaveis invalidas no seed: {invalid}. Variaveis validas: {valid_vars}"


def test_seed_macros_no_single_braces():
    """Nao deve ter {agente} com chaves simples (bug antigo)."""
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    macro_section = src[src.index("# ── Macros"):]
    # Find single-brace vars that are NOT double-brace
    single = re.findall(r'(?<!\{)\{(\w+)\}(?!\})', macro_section)
    assert not single, f"Variaveis com chaves simples (bug): {single}"


def test_seed_macros_actions_valid():
    """Actions no seed devem ter type e value validos."""
    valid_types = {"set_status", "set_priority", "add_tag", "set_category", "assign_to"}
    valid_status = {"open", "waiting", "resolved", "escalated", "closed"}
    valid_priority = {"low", "medium", "high", "urgent"}
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    macro_section = src[src.index("# ── Macros"):]
    # Extract all action dicts
    actions = re.findall(r'\{"type":\s*"(\w+)",\s*"value":\s*"([^"]+)"\}', macro_section)
    for atype, avalue in actions:
        assert atype in valid_types, f"Action type invalido: {atype}"
        if atype == "set_status":
            assert avalue in valid_status, f"Status invalido: {avalue}"
        if atype == "set_priority":
            assert avalue in valid_priority, f"Priority invalida: {avalue}"


def test_seed_macros_all_categories_represented():
    """Cada uma das 6 categorias deve ter pelo menos 1 macro."""
    required = {"meu_pedido", "garantia", "reenvio", "financeiro", "duvida", "reclamacao"}
    import re
    with open("backend/app/services/seed.py") as f:
        src = f.read()
    macro_section = src[src.index("# ── Macros"):]
    cats = set(re.findall(r'category="(\w+)"', macro_section))
    missing = required - cats
    assert not missing, f"Categorias sem macros no seed: {missing}"


# ── 1.4 Migration SQL ──

def test_migration_004_exists():
    from pathlib import Path
    p = Path("backend/migrations/004_macro_use_count.sql")
    assert p.exists(), "Migration 004 nao encontrada"


def test_migration_004_has_use_count():
    with open("backend/migrations/004_macro_use_count.sql") as f:
        sql = f.read()
    assert "use_count" in sql
    assert "INTEGER" in sql
    assert "DEFAULT 0" in sql


def test_migration_004_has_created_by():
    with open("backend/migrations/004_macro_use_count.sql") as f:
        sql = f.read()
    assert "created_by" in sql
    assert "VARCHAR" in sql


def test_migration_004_uses_if_not_exists():
    """Migration deve ser idempotente."""
    with open("backend/migrations/004_macro_use_count.sql") as f:
        sql = f.read()
    assert "IF NOT EXISTS" in sql, "Migration deve usar IF NOT EXISTS pra ser segura"
