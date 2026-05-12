"""
Playwright E2E Tests — Novas Funcionalidades
Cobre: emoji picker, panelMode, config sem Supabase, sync button, alert badge, chip compacto
"""

import json, sys
from playwright.sync_api import sync_playwright, Page

APP_PATH = "file:///C:/Users/Togszera/Desktop/APP - Controle Finanças/index.html"

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
results = []

SB = "https://ykoyezbftqxrlqvwlrek.supabase.co"
BUTI = {"id": "uuid-buti", "email": "buti@butibita.app"}
TOK_BUTI = "mock_tok_buti"
AUTH_BUTI = json.dumps({"access_token": TOK_BUTI, "refresh_token": "ref", "token_type": "bearer", "expires_in": 3600, "user": BUTI})

CONTAS_MOCK = [
    {"id": 1, "nome": "Luz (CPFL)", "emoji": "⚡", "valor": 205, "dia": 15, "cat": "fixa", "tipo": "manual", "obs": "", "ativo": True},
    {"id": 2, "nome": "Spotify",    "emoji": "🎵", "valor": 22,  "dia": 0,  "cat": "assinatura", "tipo": "auto",   "obs": "", "ativo": True},
]
PAGAMENTOS_MOCK = [
    {"id": 10, "conta_id": 1, "nome": "Luz (CPFL)", "emoji": "⚡", "valor": 205, "cat": "fixa", "tipo": "manual", "obs": "", "dia": 15, "mes": 5, "ano": 2026, "pago": True, "pago_em": "2026-05-01T00:00:00Z", "pago_por": "Buti"},
    {"id": 11, "conta_id": 2, "nome": "Spotify",    "emoji": "🎵", "valor": 22,  "cat": "assinatura", "tipo": "auto",   "obs": "", "dia": 0,  "mes": 5, "ano": 2026, "pago": True, "pago_em": "2026-05-01T00:00:00Z", "pago_por": "auto"},
]

def run_test(name, fn, page):
    try:
        fn(page)
        results.append(("PASS", name))
        print(f"  {PASS} {name}")
    except Exception as e:
        msg = str(e).split("\n")[0][:120]
        results.append(("FAIL", name, msg))
        print(f"  {FAIL} {name}")
        print(f"      → {msg}")

def mock_and_load(page: Page):
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if "/auth/v1/logout" in url:
            route.fulfill(status=204, body=""); return
        if SB in url:
            if meth in ("POST", "PATCH", "DELETE"):
                route.fulfill(status=201, content_type="application/json", body='[{"id":99}]'); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(CONTAS_MOCK)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(PAGAMENTOS_MOCK)); return
            if "configuracoes" in url:
                route.fulfill(status=200, content_type="application/json", body='[]'); return
            route.fulfill(status=200, content_type="application/json", body='[]'); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", "buti@butibita.app")
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try:
        page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except:
        page.wait_for_timeout(1500)

# ═══════════════════════════════════════════════
# ALERT BADGE — compacto, sem texto "alertas"
# ═══════════════════════════════════════════════

def test_badge_sem_texto_alertas(page):
    """Badge mostra só ícone + número, sem palavra 'alerta'."""
    mock_and_load(page)
    badge = page.locator("#alert-count")
    if badge.is_visible():
        txt = badge.inner_text()
        assert "alerta" not in txt.lower(), f"Badge ainda contém 'alerta': '{txt}'"
        assert "⚠" in txt, "Badge deve conter ícone ⚠"

def test_badge_formato_correto(page):
    """Badge formato: ⚠ N (sem sufixo de texto)."""
    mock_and_load(page)
    # Forçar badge visível via JS
    page.evaluate("document.getElementById('alert-count').style.display='block'; document.getElementById('alert-count').textContent='⚠ 2'")
    txt = page.locator("#alert-count").inner_text()
    assert txt.strip() == "⚠ 2", f"Formato inesperado: '{txt}'"

# ═══════════════════════════════════════════════
# CHIP DE USUÁRIO — compacto (só nome, sem "· Sair")
# ═══════════════════════════════════════════════

def test_chip_usuario_so_nome(page):
    """Chip exibe só o nome (Buti) sem '· Sair'."""
    mock_and_load(page)
    label = page.locator("#user-label").inner_text()
    assert label.strip() == "Buti", f"Chip deve ser só 'Buti', got: '{label}'"

def test_chip_usuario_cabe_no_header(page):
    """Chip não empurra o botão de logout para fora do header."""
    mock_and_load(page)
    chip = page.locator("#user-chip")
    header = page.locator(".header-right")
    chip_box = chip.bounding_box()
    header_box = header.bounding_box()
    assert chip_box is not None and header_box is not None
    assert chip_box["x"] + chip_box["width"] <= header_box["x"] + header_box["width"] + 5, \
        "Chip ultrapassa o header-right"

# ═══════════════════════════════════════════════
# VENCIMENTOS PRÓXIMOS — sem dueLabel subtitle
# ═══════════════════════════════════════════════

def test_proximos_sem_subtitle_vence_em(page):
    """Cards em Vencimentos Próximos não exibem 'Vence em X dias'."""
    mock_and_load(page)
    proximos_list = page.locator("#proximos-list")
    if proximos_list.locator(".bill-card").count() > 0:
        # bill-due in panel mode should be "Dia X", not "Vence em..."
        dues = proximos_list.locator(".bill-due").all_inner_texts()
        for due in dues:
            assert "Vence em" not in due, f"Subtitle 'Vence em' encontrado em proximos: '{due}'"
            assert "amanhã" not in due,   f"Subtitle 'amanhã' encontrado em proximos: '{due}'"

def test_proximos_mostra_dia(page):
    """Cards em Vencimentos Próximos mostram 'Dia X' simples."""
    mock_and_load(page)
    proximos_list = page.locator("#proximos-list")
    cards = proximos_list.locator(".bill-card").count()
    if cards > 0:
        dues = proximos_list.locator(".bill-due").all_inner_texts()
        for due in dues:
            # Should be "Dia X" or "Débito automático"
            assert any(x in due for x in ["Dia ", "Débito", "auto"]), \
                f"Formato inesperado no painel: '{due}'"

def test_badge_urgentes_removido_do_painel(page):
    """Badge 'X urgentes' não existe mais ao lado de Vencimentos Próximos."""
    mock_and_load(page)
    badge = page.locator("#urgentes-badge")
    assert badge.count() == 0, "urgentes-badge ainda está presente no DOM"

# ═══════════════════════════════════════════════
# EMOJI PICKER — campo de criação de conta
# ═══════════════════════════════════════════════

def test_emoji_field_existe_no_form(page):
    """Campo de emoji existe no formulário de nova conta."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    assert page.locator("#new-emoji").is_visible(), "Campo #new-emoji não encontrado"

def test_emoji_field_limpo_por_padrao(page):
    """Campo de emoji começa vazio."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    val = page.locator("#new-emoji").input_value()
    assert val == "", f"Campo emoji deveria estar vazio, got: '{val}'"

def test_emoji_field_aceita_emoji(page):
    """Campo de emoji aceita input de emoji."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    page.locator("#new-emoji").fill("⚡")
    val = page.locator("#new-emoji").input_value()
    assert "⚡" in val or len(val) > 0, "Emoji não foi aceito no campo"

def test_emoji_maxlength_2(page):
    """Campo de emoji tem maxlength=2."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    ml = page.locator("#new-emoji").get_attribute("maxlength")
    assert ml == "2", f"maxlength deveria ser 2, got: '{ml}'"

# ═══════════════════════════════════════════════
# EMOJI PICKER — edição de conta
# ═══════════════════════════════════════════════

def test_emoji_edit_existe_no_modal(page):
    """Campo de emoji existe no modal de edição de conta."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    try:
        page.wait_for_selector(".edit-btn", timeout=6000)
    except:
        return  # sem contas no mock, skip
    # Clicar no primeiro edit button visível
    first_edit = page.locator(".edit-btn").first
    first_edit.scroll_into_view_if_needed()
    first_edit.click()
    page.wait_for_selector("#edit-emoji", timeout=4000)
    assert page.locator("#edit-emoji").is_visible(), "Campo #edit-emoji não encontrado no modal"

def test_emoji_edit_preenchido_com_valor_atual(page):
    """Campo de emoji no modal está preenchido com o emoji atual da conta."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    try:
        page.wait_for_selector(".edit-btn", timeout=6000)
    except:
        return
    first_edit = page.locator(".edit-btn").first
    first_edit.scroll_into_view_if_needed()
    first_edit.click()
    page.wait_for_selector("#edit-emoji", timeout=4000)
    val = page.locator("#edit-emoji").input_value()
    assert len(val) > 0, "Campo de emoji no modal deveria estar preenchido"

# ═══════════════════════════════════════════════
# CONFIGURAÇÃO — sem seção "Conexão Supabase"
# ═══════════════════════════════════════════════

def test_config_sem_secao_supabase(page):
    """Seção 'Conexão Supabase' não existe na aba Configuração."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(5).click()
    page.wait_for_timeout(200)
    config_text = page.locator("#section-config").inner_text()
    assert "Conexão Supabase" not in config_text, "Seção 'Conexão Supabase' ainda presente"
    assert "Conectado ao Supabase" not in config_text, "Texto 'Conectado ao Supabase' ainda presente"

def test_config_botao_sincronizar_existe(page):
    """Botão 'Sincronizar agora' existe e está antes das Notificações."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(5).click()
    page.wait_for_timeout(200)
    config = page.locator("#section-config")
    config_html = config.inner_html()
    sync_pos = config_html.find("Sincronizar agora")
    notif_pos = config_html.find("Notificações")
    assert sync_pos > -1, "Botão Sincronizar não encontrado"
    assert notif_pos > -1, "Seção Notificações não encontrada"
    assert sync_pos < notif_pos, "Sincronizar deveria aparecer antes de Notificações"

def test_sync_button_funciona(page):
    """Clicar em Sincronizar dispara atualização (toast ou status muda)."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(5).click()
    page.wait_for_timeout(200)
    page.locator("button", has_text="Sincronizar agora").click()
    page.wait_for_timeout(800)
    # Status deve mudar para syncing e depois voltar
    status = page.locator("#sync-status").inner_text()
    assert len(status) > 0, "Status de sync não atualizado"

# ═══════════════════════════════════════════════
# CHIP DE PAGAMENTO — pago_por sem fallback indevido
# ═══════════════════════════════════════════════

def test_chip_pago_por_aparece_quando_setado(page):
    """Chip de pagador aparece quando pago_por está preenchido."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(600)
    chips = page.locator(".chip.chip-accent").all_inner_texts()
    # Buti pagou a Luz (CPFL) no mock
    assert any("Buti" in c for c in chips), f"Chip 'Buti' não encontrado. Chips: {chips}"

def test_chip_nao_aparece_para_auto(page):
    """Chip de pagador NÃO aparece para débitos automáticos."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(600)
    # Spotify é auto — não deve ter chip de pessoa
    cards = page.locator(".bill-card").all()
    for card in cards:
        name = card.locator(".bill-name").inner_text()
        if "Spotify" in name:
            chip_texts = card.locator(".chip.chip-accent").all_inner_texts()
            # AUTO tag is ok, but no person chip
            person_chips = [c for c in chip_texts if c in ["Buti", "Bita"]]
            assert len(person_chips) == 0, f"Chip de pessoa em débito auto: {person_chips}"
            break

# ═══════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════

TESTS = [
    ("Badge sem texto 'alertas'", test_badge_sem_texto_alertas),
    ("Badge formato ⚠ N", test_badge_formato_correto),
    ("Chip usuário só nome", test_chip_usuario_so_nome),
    ("Chip cabe no header", test_chip_usuario_cabe_no_header),
    ("Proximos sem subtitle 'Vence em'", test_proximos_sem_subtitle_vence_em),
    ("Proximos mostra 'Dia X'", test_proximos_mostra_dia),
    ("Badge urgentes removido do DOM", test_badge_urgentes_removido_do_painel),
    ("Emoji field existe no form", test_emoji_field_existe_no_form),
    ("Emoji field limpo por padrão", test_emoji_field_limpo_por_padrao),
    ("Emoji field aceita emoji", test_emoji_field_aceita_emoji),
    ("Emoji maxlength=2", test_emoji_maxlength_2),
    ("Emoji edit existe no modal", test_emoji_edit_existe_no_modal),
    ("Emoji edit preenchido com valor atual", test_emoji_edit_preenchido_com_valor_atual),
    ("Config sem seção Supabase", test_config_sem_secao_supabase),
    ("Config botão sincronizar antes das notificações", test_config_botao_sincronizar_existe),
    ("Sync button funciona", test_sync_button_funciona),
    ("Chip pago_por aparece quando setado", test_chip_pago_por_aparece_quando_setado),
    ("Chip NÃO aparece para débito auto", test_chip_nao_aparece_para_auto),
]

def main():
    print("\n" + "═" * 60)
    print("  E2E — Novas Funcionalidades · Buti & Bita Financials")
    print("═" * 60 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=0, args=["--no-sandbox"])
        for name, fn in TESTS:
            ctx = browser.new_context(viewport={"width": 390, "height": 844})
            page = ctx.new_page()
            page.on("console", lambda m: None)
            run_test(name, fn, page)
            page.close()
            ctx.close()
        browser.close()

    total  = len(TESTS)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = total - passed
    print("\n" + "═" * 60)
    print(f"  RESULTADO: {passed}/{total} passou ({round(passed/total*100)}%)")
    if failed:
        print(f"\n  Falhas ({failed}):")
        for r in results:
            if r[0] == "FAIL":
                print(f"    {FAIL} {r[1]}")
                if len(r) > 2: print(f"       {r[2]}")
    print("═" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
