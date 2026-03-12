"""
CAMADA 3: Frontend Logic (sem browser)
Testa a logica JS/JSX via analise estatica do codigo-fonte.
Verifica consistencia entre frontend e backend.
"""
import pytest
import re
import json


def read_file(path):
    with open(path) as f:
        return f.read()


MACROS_PAGE = "frontend/src/pages/MacrosPage.jsx"
TICKET_DETAIL = "frontend/src/pages/TicketDetailPage.jsx"
API_JS = "frontend/src/services/api.js"


# ── 3.1 Categorias alinhadas ──

def test_frontend_categories_match_backend():
    """MacrosPage deve ter as mesmas 6 categorias do ai_service."""
    frontend_src = read_file(MACROS_PAGE)
    backend_src = read_file("backend/app/services/ai_service.py")

    # Extract frontend categories
    fe_cats = set(re.findall(r"value:\s*'(\w+)'", frontend_src.split("MACRO_CATEGORIES")[1].split("]")[0]))

    # Extract backend categories
    be_cats = set(re.findall(r"- (\w+):", backend_src[backend_src.index("CATEGORIAS"):backend_src.index("REGRA")]))

    assert fe_cats == be_cats, f"Frontend {fe_cats} != Backend {be_cats}"


def test_frontend_no_old_categories():
    """Nao pode ter categorias antigas."""
    src = read_file(MACROS_PAGE)
    old = ["'geral'", "'troca'", "'rastreamento'"]
    for cat in old:
        assert cat not in src, f"Categoria antiga encontrada no MacrosPage: {cat}"


def test_action_types_categories_match():
    """ACTION_TYPES set_category deve ter as mesmas categorias."""
    src = read_file(MACROS_PAGE)
    # Extract set_category options
    action_section = src[src.index("set_category"):]
    options_match = re.search(r"options:\s*\[([^\]]+)\]", action_section)
    assert options_match, "set_category nao tem options"
    options = set(re.findall(r"'(\w+)'", options_match.group(1)))
    expected = {"meu_pedido", "garantia", "reenvio", "financeiro", "duvida", "reclamacao"}
    assert options == expected, f"ACTION_TYPES categories {options} != {expected}"


# ── 3.2 Variavel {{agente}} ──

def test_variables_include_agente():
    """VARIABLES deve ter {{agente}}."""
    src = read_file(MACROS_PAGE)
    assert "{{agente}}" in src, "{{agente}} nao esta nas VARIABLES"


def test_preview_replaces_agente():
    """Preview no MacrosPage deve substituir {{agente}}."""
    src = read_file(MACROS_PAGE)
    assert "agente" in src and "Ana Silva" in src, "Preview nao substitui {{agente}}"


def test_apply_macro_vars_has_agente():
    """applyMacroVars no TicketDetailPage deve substituir {{agente}}."""
    src = read_file(TICKET_DETAIL)
    func_section = src[src.index("function applyMacroVars"):src.index("function applyMacroVars") + 500]
    assert "agente" in func_section, "applyMacroVars nao trata {{agente}}"


def test_apply_macro_vars_receives_agent_name():
    """applyMacroVars deve receber agentName como parametro."""
    src = read_file(TICKET_DETAIL)
    assert "function applyMacroVars(content, ticket, agentName)" in src


def test_apply_macro_vars_called_with_user_name():
    """Todas as chamadas de applyMacroVars devem passar user?.name."""
    src = read_file(TICKET_DETAIL)
    calls = re.findall(r"applyMacroVars\([^)]+\)", src)
    # Filter out the function definition
    usage_calls = [c for c in calls if "function" not in c and "content, ticket, agentName" not in c]
    for call in usage_calls:
        assert "user?.name" in call, f"Chamada sem user?.name: {call}"


# ── 3.3 Actions UI ──

def test_macros_page_has_action_types():
    """MacrosPage deve ter ACTION_TYPES definido."""
    src = read_file(MACROS_PAGE)
    assert "ACTION_TYPES" in src


def test_macros_page_has_actions_in_form():
    """Empty form deve ter actions: []."""
    src = read_file(MACROS_PAGE)
    assert "actions: []" in src, "EMPTY_FORM nao tem actions"


def test_macros_page_renders_action_editor():
    """MacrosPage deve ter UI pra editar actions."""
    src = read_file(MACROS_PAGE)
    assert "Acoes automaticas" in src
    assert "Adicionar" in src


def test_macros_page_action_remove_button():
    """Deve ter botao pra remover action."""
    src = read_file(MACROS_PAGE)
    assert "fa-times" in src  # remove button icon


def test_macros_page_filters_empty_actions():
    """Save deve filtrar actions sem value."""
    src = read_file(MACROS_PAGE)
    assert "filter(a => a.type && a.value)" in src


# ── 3.4 Use count ──

def test_api_has_track_macro_use():
    """api.js deve exportar trackMacroUse."""
    src = read_file(API_JS)
    assert "trackMacroUse" in src
    assert "/use" in src


def test_ticket_detail_imports_track_macro_use():
    """TicketDetailPage deve importar trackMacroUse."""
    src = read_file(TICKET_DETAIL)
    assert "trackMacroUse" in src


def test_ticket_detail_calls_track_on_slash():
    """handleSlashSelect deve chamar trackMacroUse."""
    src = read_file(TICKET_DETAIL)
    slash_section = src[src.index("handleSlashSelect"):src.index("handleMacroClick")]
    assert "trackMacroUse(macro.id)" in slash_section


def test_ticket_detail_calls_track_on_click():
    """handleMacroClick deve chamar trackMacroUse."""
    src = read_file(TICKET_DETAIL)
    click_section = src[src.index("handleMacroClick"):src.index("handleMacroSendDirect")]
    assert "trackMacroUse(macro.id)" in click_section


def test_ticket_detail_calls_track_on_direct_send():
    """handleMacroSendDirect deve chamar trackMacroUse."""
    src = read_file(TICKET_DETAIL)
    send_section = src[src.index("handleMacroSendDirect"):src.index("handleMacroSendDirect") + 500]
    assert "trackMacroUse(macro.id)" in send_section


def test_track_macro_use_is_fire_and_forget():
    """trackMacroUse deve ter .catch(() => {}) pra nao bloquear."""
    src = read_file(TICKET_DETAIL)
    track_calls = re.findall(r"trackMacroUse\(macro\.id\)[^;]*", src)
    for call in track_calls:
        assert ".catch" in call, f"trackMacroUse sem .catch (pode bloquear UI): {call}"


def test_macros_page_shows_use_count_badge():
    """MacrosPage deve mostrar badge de uso nos cards."""
    src = read_file(MACROS_PAGE)
    assert "use_count" in src
    assert "usada" in src


# ── 3.5 Consistencia geral ──

def test_macros_page_no_geral_default():
    """EMPTY_FORM nao deve defaultar pra 'geral' (categoria antiga)."""
    src = read_file(MACROS_PAGE)
    empty_form = src[src.index("EMPTY_FORM"):src.index("EMPTY_FORM") + 100]
    assert "'geral'" not in empty_form


def test_start_edit_loads_actions():
    """startEdit deve carregar actions da macro."""
    src = read_file(MACROS_PAGE)
    edit_section = src[src.index("startEdit"):src.index("startEdit") + 200]
    assert "actions:" in edit_section
    assert "macro.actions" in edit_section


def test_macros_dropdown_in_ticket_detail():
    """TicketDetailPage deve mostrar macros no dropdown."""
    src = read_file(TICKET_DETAIL)
    assert "showMacros" in src
    assert "setShowMacros" in src


def test_slash_command_still_works():
    """Slash command / deve continuar funcionando."""
    src = read_file(TICKET_DETAIL)
    assert "slashOpen" in src
    assert "slashFilter" in src
    assert "handleSlashSelect" in src
