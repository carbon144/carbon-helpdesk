"""
CAMADA 2: API routes + integration logic
Testa integridade das rotas, imports, e logica via analise do codigo.
(SQLAlchemy incompativel com Python 3.14 local — runtime tests rodam no Docker/prod)
"""
import pytest
import re
import ast


def read_file(path):
    with open(path) as f:
        return f.read()


KB_API = "backend/app/api/kb.py"
MAIN = "backend/app/main.py"
SCHEMAS = "backend/app/schemas/kb.py"


# ── 2.1 Route registration ──

def test_kb_router_registered_in_main():
    """kb router deve estar registrado no main.py."""
    src = read_file(MAIN)
    assert "from app.api" in src
    assert "kb" in src


def test_kb_router_has_prefix():
    src = read_file(KB_API)
    assert 'prefix="/kb"' in src


# ── 2.2 Macro CRUD endpoints exist ──

def test_list_macros_endpoint():
    src = read_file(KB_API)
    assert '@router.get("/macros"' in src
    assert "list_macros" in src


def test_create_macro_endpoint():
    src = read_file(KB_API)
    assert '@router.post("/macros"' in src
    assert "create_macro" in src
    assert "status_code=201" in src


def test_update_macro_endpoint():
    src = read_file(KB_API)
    assert '@router.patch("/macros/{macro_id}"' in src
    assert "update_macro" in src


def test_delete_macro_endpoint():
    src = read_file(KB_API)
    assert '@router.delete("/macros/{macro_id}"' in src
    assert "delete_macro" in src


# ── 2.3 Track use endpoint (NEW) ──

def test_track_use_endpoint_exists():
    src = read_file(KB_API)
    assert '@router.post("/macros/{macro_id}/use")' in src
    assert "track_macro_use" in src


def test_track_use_increments_count():
    """track_macro_use deve incrementar use_count."""
    src = read_file(KB_API)
    # Find the track_macro_use function
    func_start = src.index("async def track_macro_use")
    func_end = src.index("\n\n", func_start)
    func_body = src[func_start:func_end]
    assert "use_count" in func_body
    assert "+ 1" in func_body


def test_track_use_returns_count():
    """track_macro_use deve retornar o use_count atualizado."""
    src = read_file(KB_API)
    func_start = src.index("async def track_macro_use")
    func_end = src.index("\n\n", func_start)
    func_body = src[func_start:func_end]
    assert '"use_count"' in func_body


def test_track_use_handles_none():
    """use_count or 0 — handles None gracefully."""
    src = read_file(KB_API)
    func_start = src.index("async def track_macro_use")
    func_end = src.index("\n\n", func_start)
    func_body = src[func_start:func_end]
    assert "or 0" in func_body, "Deve tratar use_count=None com fallback 0"


def test_track_use_404_on_missing():
    """track_macro_use deve retornar 404 se macro nao existe."""
    src = read_file(KB_API)
    func_start = src.index("async def track_macro_use")
    func_end = src.index("\n\n", func_start)
    func_body = src[func_start:func_end]
    assert "404" in func_body


# ── 2.4 Auth on all endpoints ──

def test_all_macro_endpoints_require_auth():
    """Todos os endpoints de macro devem ter get_current_user."""
    src = read_file(KB_API)
    macro_section = src[src.index("# ── Macros ──"):]
    funcs = re.findall(r"async def (\w+)\(", macro_section)
    for func_name in funcs:
        func_start = macro_section.index(f"async def {func_name}")
        # Get full signature (may span multiple lines until ):)
        func_sig_end = macro_section.index("):", func_start) + 2
        sig = macro_section[func_start:func_sig_end]
        assert "get_current_user" in sig, f"{func_name} nao exige autenticacao!"


# ── 2.5 Create macro handles actions ──

def test_create_macro_processes_actions():
    """create_macro deve processar actions (model_dump)."""
    src = read_file(KB_API)
    func_start = src.index("async def create_macro")
    func_end = src.index("async def update_macro")
    func_body = src[func_start:func_end]
    assert "actions" in func_body
    assert "model_dump" in func_body


def test_update_macro_processes_actions():
    """update_macro deve processar actions."""
    src = read_file(KB_API)
    func_start = src.index("async def update_macro")
    func_end = src.index("async def", func_start + 10)
    func_body = src[func_start:func_end]
    assert "actions" in func_body


# ── 2.6 Response schemas ──

def test_list_macros_returns_macro_response():
    src = read_file(KB_API)
    assert "list[MacroResponse]" in src


def test_create_returns_macro_response():
    src = read_file(KB_API)
    # Decorator and function may be on separate lines — check the line before create_macro
    lines = src.split("\n")
    for i, line in enumerate(lines):
        if "async def create_macro" in line:
            decorator = lines[i - 1]
            assert "MacroResponse" in decorator, f"create_macro decorator faltando MacroResponse: {decorator}"
            break


def test_macro_response_has_all_fields():
    """MacroResponse deve ter todos os campos necessarios."""
    src = read_file(SCHEMAS)
    response_section = src[src.index("class MacroResponse"):]
    required_fields = ["id", "name", "content", "category", "is_active", "actions", "use_count", "created_by"]
    for field in required_fields:
        assert field in response_section, f"MacroResponse faltando campo: {field}"


# ── 2.7 Schema imports ──

def test_kb_api_imports_schemas():
    src = read_file(KB_API)
    assert "MacroCreate" in src
    assert "MacroUpdate" in src
    assert "MacroResponse" in src


def test_kb_api_imports_macro_model():
    src = read_file(KB_API)
    assert "from app.models.macro import Macro" in src


# ── 2.8 Endpoint order (track_use before delete) ──

def test_track_use_before_delete():
    """POST /use deve vir antes de DELETE pra evitar conflito de rota."""
    src = read_file(KB_API)
    track_pos = src.index("track_macro_use")
    delete_pos = src.index("delete_macro")
    assert track_pos < delete_pos, "track_macro_use deve estar antes de delete_macro no arquivo"


# ── 2.9 Frontend API client matches backend ──

def test_api_js_has_all_macro_endpoints():
    """api.js deve ter funcoes pra todos os endpoints de macro."""
    src = read_file("frontend/src/services/api.js")
    required = ["getMacros", "createMacro", "updateMacro", "deleteMacro", "trackMacroUse"]
    for fn in required:
        assert fn in src, f"api.js faltando: {fn}"


def test_api_js_track_macro_use_url():
    """trackMacroUse deve chamar POST /kb/macros/{id}/use."""
    src = read_file("frontend/src/services/api.js")
    track_line = [l for l in src.split("\n") if "trackMacroUse" in l][0]
    assert "/use" in track_line
    assert "post" in track_line.lower()


# ── 2.10 Stress: all routes are parseable Python ──

def test_kb_api_is_valid_python():
    """kb.py deve ser Python valido."""
    src = read_file(KB_API)
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"kb.py tem erro de sintaxe: {e}")


def test_schemas_is_valid_python():
    src = read_file(SCHEMAS)
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"schemas/kb.py tem erro de sintaxe: {e}")


def test_macro_model_is_valid_python():
    src = read_file("backend/app/models/macro.py")
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"models/macro.py tem erro de sintaxe: {e}")


def test_seed_is_valid_python():
    src = read_file("backend/app/services/seed.py")
    try:
        ast.parse(src)
    except SyntaxError as e:
        pytest.fail(f"seed.py tem erro de sintaxe: {e}")
