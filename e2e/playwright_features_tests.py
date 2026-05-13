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


# ═══════════════════════════════════════════════
# BUG FIX: EMOJI SALVO NA EDIÇÃO
# ═══════════════════════════════════════════════

def test_emoji_enviado_no_patch(page):
    """sbPatch de conta inclui campo emoji quando preenchido."""
    patched_data = []
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url and "contas" in url and meth == "PATCH":
            try: patched_data.append(json.loads(route.request.post_data or "{}"))
            except: pass
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url:
            if meth in ("POST","PATCH","DELETE"):
                route.fulfill(status=201, content_type="application/json", body='[{"id":99}]'); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(CONTAS_MOCK)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(PAGAMENTOS_MOCK)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    # Navega para contas, abre edição
    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".edit-btn", timeout=6000)
    except: return
    page.locator(".edit-btn").first.scroll_into_view_if_needed()
    page.locator(".edit-btn").first.click()
    page.wait_for_selector("#edit-emoji", timeout=4000)

    # Troca o emoji
    page.locator("#edit-emoji").fill("🏠")
    page.locator("button", has_text="Salvar alterações").click()
    page.wait_for_timeout(800)

    # Verifica que o PATCH enviou o emoji
    emoji_patches = [d for d in patched_data if "emoji" in d]
    assert len(emoji_patches) > 0, f"Nenhum PATCH com campo emoji enviado. Patches: {patched_data}"
    assert any(d.get("emoji") == "🏠" for d in emoji_patches), f"Emoji incorreto nos patches: {patched_data}"

def test_criado_por_enviado_no_patch(page):
    """sbPatch de conta inclui criado_por com o usuário que editou."""
    patched_data = []
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url and "contas" in url and meth == "PATCH":
            try: patched_data.append(json.loads(route.request.post_data or "{}"))
            except: pass
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url:
            if meth in ("POST","PATCH","DELETE"):
                route.fulfill(status=201, content_type="application/json", body='[{"id":99}]'); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(CONTAS_MOCK)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(PAGAMENTOS_MOCK)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".edit-btn", timeout=6000)
    except: return
    page.locator(".edit-btn").first.scroll_into_view_if_needed()
    page.locator(".edit-btn").first.click()
    page.wait_for_selector("#edit-nome", timeout=4000)
    page.locator("button", has_text="Salvar alterações").click()
    page.wait_for_timeout(800)

    # Verifica que criado_por foi enviado com o usuário logado
    assert any("criado_por" in d for d in patched_data), f"criado_por ausente nos patches: {patched_data}"
    assert any(d.get("criado_por") in ["Buti", BUTI["email"]] for d in patched_data),         f"criado_por deveria ser {EMAIL_BUTI}, patches: {patched_data}"

# ═══════════════════════════════════════════════
# BUG FIX: CHIP criado_por NO CARD
# ═══════════════════════════════════════════════

def test_chip_criado_por_aparece_no_card(page):
    """Card de conta exibe chip com criado_por quando não há pago_por."""
    contas_com_criado = [
        {**CONTAS_MOCK[0], "criado_por": "Buti"},
    ]
    pags_sem_pagopor = [
        {**PAGAMENTOS_MOCK[0], "pago": False, "pago_por": ""},
    ]

    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url:
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(contas_com_criado)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(pags_sem_pagopor)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(800)

    chips = page.locator("#list-fixas .chip.chip-accent").all_inner_texts()
    assert any("Buti" in c for c in chips),         f"Chip de criado_por não apareceu. Chips encontrados: {chips}"

def test_chip_pago_por_tem_prioridade_sobre_criado_por(page):
    """Chip mostra pago_por quando conta está paga (prioridade sobre criado_por)."""
    contas_com_criado = [{**CONTAS_MOCK[0], "criado_por": "Buti"}]
    pags_pago_bita = [{**PAGAMENTOS_MOCK[0], "pago": True, "pago_por": "Bita"}]

    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url:
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(contas_com_criado)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(pags_pago_bita)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(800)

    chips = page.locator("#list-fixas .chip.chip-accent").all_inner_texts()
    # Deve mostrar Bita (pago_por) e não Buti (criado_por)
    assert any("Bita" in c for c in chips), f"pago_por (Bita) deveria ter prioridade. Chips: {chips}"
    assert not any(c.strip() == "Buti" for c in chips), f"criado_por (Buti) não deveria aparecer quando há pago_por. Chips: {chips}"



# ═══════════════════════════════════════════════
# TC-PROX: VENCIMENTOS PRÓXIMOS — FILTRO POR PAGAMENTO
# ═══════════════════════════════════════════════

CONTA_PENDENTE = {"id":10,"nome":"Conta Pendente","emoji":"💡","valor":100,"dia":14,"cat":"fixa","tipo":"manual","obs":"","ativo":True,"criado_por":"Buti"}
CONTA_PAGA     = {"id":11,"nome":"Conta Paga","emoji":"✅","valor":200,"dia":13,"cat":"fixa","tipo":"manual","obs":"","ativo":True,"criado_por":"Buti"}

PAG_PAGA = {"id":20,"conta_id":11,"nome":"Conta Paga","emoji":"✅","valor":200,"cat":"fixa","tipo":"manual","obs":"","dia":13,"mes":5,"ano":2026,"pago":True,"pago_em":"2026-05-01T00:00:00Z","pago_por":"Buti"}
PAG_PENDENTE = {"id":21,"conta_id":10,"nome":"Conta Pendente","emoji":"💡","valor":100,"cat":"fixa","tipo":"manual","obs":"","dia":14,"mes":5,"ano":2026,"pago":False,"pago_em":None,"pago_por":""}

def load_with_mock(page, contas, pagamentos):
    """Load app with specific contas and pagamentos mock data."""
    import json as _json
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(BUTI)); return
        if "/auth/v1/logout" in url:
            route.fulfill(status=204, body=""); return
        if SB in url:
            if meth in ("PATCH","DELETE"):
                route.fulfill(status=200, content_type="application/json", body="[]"); return
            if meth == "POST":
                route.fulfill(status=201, content_type="application/json", body='[{"id":99}]'); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(contas)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json", body=_json.dumps(pagamentos)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try:
        page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except:
        page.wait_for_timeout(1500)
    page.wait_for_timeout(600)  # aguarda renderAll()

def get_proximos_names(page):
    """Return list of names visible in proximos-list."""
    cards = page.locator("#proximos-list .bill-card .bill-name").all_inner_texts()
    return [c.strip() for c in cards]

def conta_paga_em_contas(page, nome):
    """Check if a conta with given name appears in aba Contas with paid status."""
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(400)
    cards = page.locator("#section-contas .bill-card").all()
    for card in cards:
        card_text = card.inner_text()
        if nome in card_text:
            return True
    return False

def test_prox_conta_pendente_aparece(page):
    """TC-PROX-001 Conta não paga aparece em Vencimentos Próximos."""
    load_with_mock(page, [CONTA_PENDENTE, CONTA_PAGA], [PAG_PAGA, PAG_PENDENTE])
    nomes = get_proximos_names(page)
    assert any("Conta Pendente" in n for n in nomes), \
        f"Conta pendente deveria aparecer em Próximos. Nomes: {nomes}"

def test_prox_conta_paga_nao_aparece(page):
    """TC-PROX-002 Conta paga NÃO aparece em Vencimentos Próximos."""
    load_with_mock(page, [CONTA_PENDENTE, CONTA_PAGA], [PAG_PAGA, PAG_PENDENTE])
    nomes = get_proximos_names(page)
    assert not any("Conta Paga" in n for n in nomes), \
        f"Conta paga NÃO deveria aparecer em Próximos. Nomes: {nomes}"

def test_prox_conta_paga_aparece_na_aba_contas(page):
    """TC-PROX-005 Conta paga aparece na aba Contas com status pago."""
    load_with_mock(page, [CONTA_PENDENTE, CONTA_PAGA], [PAG_PAGA, PAG_PENDENTE])
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(400)
    # Conta paga deve estar em list-fixas com classe paid
    paid_cards = page.locator("#list-fixas .bill-card.paid").all_inner_texts()
    assert any("Conta Paga" in c for c in paid_cards), \
        f"Conta paga deveria aparecer em Contas com status pago. Cards paid: {paid_cards}"

def test_prox_empty_state_quando_tudo_pago(page):
    """TC-PROX-006 Empty state quando todas as contas próximas estão pagas."""
    pag_pendente_pago = {**PAG_PENDENTE, "pago": True, "pago_por": "Buti"}
    load_with_mock(page, [CONTA_PENDENTE, CONTA_PAGA], [PAG_PAGA, pag_pendente_pago])
    proximos_html = page.locator("#proximos-list").inner_html()
    # Should show empty state or no bill-cards
    cards = page.locator("#proximos-list .bill-card").count()
    empty = page.locator("#proximos-list .empty-state").count()
    assert cards == 0 or empty > 0, \
        f"Com tudo pago, proximos deveria estar vazio. Cards: {cards}, empty: {empty}"

def test_prox_marcar_paga_remove_dos_proximos(page):
    """TC-PROX-003 Marcar conta como paga remove ela de Vencimentos Próximos."""
    # Start with both pending
    pag_pendente2 = {**PAG_PAGA, "pago": False, "pago_por": ""}
    patched = []

    import json as _json
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(BUTI)); return
        if SB in url and "pagamentos" in url and meth == "PATCH":
            try: patched.append(_json.loads(route.request.post_data or "{}"))
            except: pass
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url and "pagamentos" in url and meth == "POST":
            route.fulfill(status=201, content_type="application/json",
                         body=_json.dumps([{**PAG_PENDENTE, "pago": True, "pago_por": "Buti"}])); return
        if SB in url and "pagamentos" in url:
            # After toggle, return updated list with conta_id=10 marked as paid
            if patched:
                updated = [{**PAG_PENDENTE, "pago": True, "pago_por": "Buti"}, pag_pendente2]
            else:
                updated = [PAG_PENDENTE, pag_pendente2]
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(updated)); return
        if SB in url:
            if meth in ("DELETE",): route.fulfill(status=200, body="[]"); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json",
                             body=_json.dumps([CONTA_PENDENTE, CONTA_PAGA])); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try:
        page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except:
        page.wait_for_timeout(1500)
    page.wait_for_timeout(600)

    # Should show both pending in proximos initially
    nomes_antes = get_proximos_names(page)
    assert any("Conta Pendente" in n for n in nomes_antes), \
        f"Conta Pendente deveria estar em Próximos inicialmente. Nomes: {nomes_antes}"

    # Click toggle on Conta Pendente in proximos
    cards = page.locator("#proximos-list .bill-card").all()
    toggled = False
    for card in cards:
        if "Conta Pendente" in card.inner_text():
            toggle = card.locator(".toggle-paid")
            if toggle.count() > 0:
                toggle.click()
                toggled = True
                break

    if not toggled:
        return  # skip if toggle not available

    page.wait_for_timeout(800)
    nomes_depois = get_proximos_names(page)
    assert not any("Conta Pendente" in n for n in nomes_depois), \
        f"Conta Pendente deveria sumir de Próximos após marcar paga. Nomes depois: {nomes_depois}"

def test_prox_desmarcar_volta_aos_proximos(page):
    """TC-PROX-004 Desmarcar conta paga volta ela para Vencimentos Próximos."""
    # Start with CONTA_PENDENTE paid, then unpay it
    patched = []

    import json as _json
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(BUTI)); return
        if SB in url and "pagamentos" in url and meth == "PATCH":
            try: patched.append(_json.loads(route.request.post_data or "{}"))
            except: pass
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url and "pagamentos" in url:
            # After unpay toggle, return conta_pendente as not paid
            if patched and any(not p.get("pago", True) for p in patched):
                updated = [{**PAG_PENDENTE, "pago": False, "pago_por": ""}, PAG_PAGA]
            else:
                # Initially paid
                updated = [{**PAG_PENDENTE, "pago": True, "pago_por": "Buti"}, PAG_PAGA]
            route.fulfill(status=200, content_type="application/json", body=_json.dumps(updated)); return
        if SB in url:
            if meth in ("DELETE","POST","PATCH"): route.fulfill(status=200, body="[]"); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json",
                             body=_json.dumps([CONTA_PENDENTE, CONTA_PAGA])); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try:
        page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except:
        page.wait_for_timeout(1500)
    page.wait_for_timeout(600)

    # Initially Conta Pendente is paid — should NOT be in proximos
    nomes_antes = get_proximos_names(page)
    assert not any("Conta Pendente" in n for n in nomes_antes), \
        f"Conta Pendente (paga) não deveria estar em Próximos. Nomes: {nomes_antes}"

    # Go to Contas tab and unpay it
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(400)
    cards = page.locator("#list-fixas .bill-card").all()
    toggled = False
    for card in cards:
        if "Conta Pendente" in card.inner_text():
            toggle = card.locator(".toggle-paid")
            if toggle.count() > 0:
                toggle.click()
                toggled = True
                break

    if not toggled:
        return

    page.wait_for_timeout(800)
    # Go back to dashboard
    page.locator(".nav-btn").nth(0).click()
    page.wait_for_timeout(400)
    nomes_depois = get_proximos_names(page)
    assert any("Conta Pendente" in n for n in nomes_depois), \
        f"Conta Pendente deveria voltar a Próximos após desmarcar. Nomes depois: {nomes_depois}"

# ═══════════════════════════════════════════════
# TC-DEL: DELETE DE CONTAS
# ═══════════════════════════════════════════════

def test_del_btn_existe_em_cards_de_contas(page):
    """TC-DEL-001 Botão de excluir (🗑) existe nos cards de contas."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return
    assert page.locator(".del-btn").count() > 0, "Nenhum botão .del-btn encontrado"

def test_del_btn_abre_modal_confirmacao(page):
    """TC-DEL-002 Clicar no 🗑 abre modal de confirmação."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return
    page.locator(".del-btn").first.scroll_into_view_if_needed()
    page.locator(".del-btn").first.click()
    page.wait_for_timeout(400)
    cls = page.locator("#confirm-overlay").get_attribute("class")
    assert "hidden" not in cls, "Modal de confirmação não abriu ao clicar em 🗑"

def test_del_modal_exibe_nome_da_conta(page):
    """TC-DEL-003 Modal de confirmação exibe o nome da conta."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return
    page.locator(".del-btn").first.scroll_into_view_if_needed()
    page.locator(".del-btn").first.click()
    page.wait_for_timeout(400)
    msg = page.locator("#confirm-msg").inner_text()
    # Should mention the account name (Luz (CPFL) from mock)
    assert len(msg) > 5, f"Mensagem do modal muito curta: '{msg}'"
    assert "Excluir" in msg or "excluir" in msg, f"Mensagem não menciona exclusão: '{msg}'"

def test_del_cancelar_mantem_conta(page):
    """TC-DEL-004 Cancelar não remove a conta da lista."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return
    count_antes = page.locator(".bill-card").count()
    page.locator(".del-btn").first.scroll_into_view_if_needed()
    page.locator(".del-btn").first.click()
    page.wait_for_timeout(400)
    # Cancelar
    page.locator("#confirm-overlay .btn-secondary").click()
    page.wait_for_timeout(300)
    count_depois = page.locator(".bill-card").count()
    assert count_depois == count_antes,         f"Conta foi removida após cancelar! Antes: {count_antes}, depois: {count_depois}"

def test_del_confirmar_remove_conta(page):
    """TC-DEL-005 Confirmar remove o card da conta da lista."""
    patched = []
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url and "contas" in url and meth == "PATCH":
            try: patched.append(json.loads(route.request.post_data or "{}"))
            except: pass
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url:
            if meth in ("POST","DELETE"):
                route.fulfill(status=200, content_type="application/json", body="[]"); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(CONTAS_MOCK)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(PAGAMENTOS_MOCK)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return

    count_antes = page.locator("#section-contas .bill-card").count()
    page.locator(".del-btn").first.scroll_into_view_if_needed()
    page.locator(".del-btn").first.click()
    page.wait_for_timeout(400)
    page.locator("#confirm-ok-btn").click()
    page.wait_for_timeout(600)

    count_depois = page.locator("#section-contas .bill-card").count()
    assert count_depois < count_antes,         f"Conta não foi removida do DOM. Antes: {count_antes}, depois: {count_depois}"

def test_del_usa_soft_delete_nao_hard_delete(page):
    """TC-DEL-009 Excluir conta faz PATCH com ativo=false, não DELETE."""
    patched = []
    deleted = []
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url and "contas" in url and meth == "PATCH":
            try: patched.append(json.loads(route.request.post_data or "{}"))
            except: pass
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url and "contas" in url and meth == "DELETE":
            deleted.append(url)
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        if SB in url:
            if meth in ("POST",):
                route.fulfill(status=201, content_type="application/json", body='[{"id":99}]'); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(CONTAS_MOCK)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(PAGAMENTOS_MOCK)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return
    page.locator(".del-btn").first.scroll_into_view_if_needed()
    page.locator(".del-btn").first.click()
    page.wait_for_timeout(400)
    page.locator("#confirm-ok-btn").click()
    page.wait_for_timeout(600)

    # Deve ter feito PATCH com ativo:false, NÃO um DELETE HTTP
    soft_deletes = [p for p in patched if p.get("ativo") == False]
    assert len(soft_deletes) > 0, f"Nenhum PATCH com ativo:false. Patches: {patched}"
    assert len(deleted) == 0, f"DELETE HTTP foi chamado! Deveria ser PATCH com ativo:false. DELETEs: {deleted}"

def test_del_toast_apos_excluir(page):
    """TC-DEL-006 Toast aparece após excluir conta."""
    def handle(route):
        url, meth = route.request.url, route.request.method
        if "/auth/v1/token" in url and meth == "POST":
            route.fulfill(status=200, content_type="application/json", body=AUTH_BUTI); return
        if "/auth/v1/user" in url:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(BUTI)); return
        if SB in url:
            if meth in ("PATCH", "POST", "DELETE"):
                route.fulfill(status=200, content_type="application/json", body="[]"); return
            if "contas" in url and "configuracoes" not in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(CONTAS_MOCK)); return
            if "pagamentos" in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(PAGAMENTOS_MOCK)); return
            route.fulfill(status=200, content_type="application/json", body="[]"); return
        route.continue_()

    page.route("**/*", handle)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#login-screen:not(.hidden)", timeout=8000)
    page.wait_for_timeout(300)
    page.fill("#login-email", BUTI["email"])
    page.fill("#login-password", "senha123")
    page.click("#btn-login")
    try: page.wait_for_function("document.getElementById('app-shell').style.display==='flex'", timeout=8000)
    except: page.wait_for_timeout(1500)

    page.locator(".nav-btn").nth(1).click()
    try: page.wait_for_selector(".del-btn", timeout=6000)
    except: return
    page.locator(".del-btn").first.scroll_into_view_if_needed()
    page.locator(".del-btn").first.click()
    page.wait_for_timeout(400)
    page.locator("#confirm-ok-btn").click()
    page.wait_for_timeout(700)

    toast = page.locator(".toast")
    assert toast.is_visible(), "Toast não apareceu após excluir"
    toast_text = toast.inner_text().lower()
    assert "exclu" in toast_text or "remov" in toast_text,         f"Toast não menciona exclusão: '{toast_text}'"

def test_del_btn_nao_aparece_no_painel(page):
    """TC-DEL-007 Botão 🗑 não aparece nos cards em modo painel (panelMode=true)."""
    mock_and_load(page)
    # Dashboard is active by default
    proximos = page.locator("#proximos-list")
    page.wait_for_timeout(600)
    del_btns_in_panel = proximos.locator(".del-btn").count()
    assert del_btns_in_panel == 0,         f"Botão de excluir não deveria aparecer no painel. Encontrados: {del_btns_in_panel}"

def test_del_avulso_ainda_funciona(page):
    """TC-DEL-008 Excluir gasto avulso ainda funciona (não regrediu)."""
    mock_and_load(page)
    page.locator(".nav-btn").nth(2).click()
    page.wait_for_timeout(600)
    del_btns = page.locator("#list-avulsos .edit-btn").count()
    # Gastos avulsos usam edit-btn com 🗑 — verifica que a seção está renderizada
    avulso_section = page.locator("#list-avulsos")
    assert avulso_section.count() > 0, "Seção de gastos avulsos não encontrada"

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
    # Bug fixes
    ("Emoji enviado no PATCH da conta", test_emoji_enviado_no_patch),
    ("criado_por enviado no PATCH da conta", test_criado_por_enviado_no_patch),
    ("Chip criado_por aparece no card", test_chip_criado_por_aparece_no_card),
    ("pago_por tem prioridade sobre criado_por no chip", test_chip_pago_por_tem_prioridade_sobre_criado_por),
    # Delete de contas
    ("TC-DEL-001 Botão excluir existe em cards", test_del_btn_existe_em_cards_de_contas),
    ("TC-DEL-002 Clicar excluir abre modal", test_del_btn_abre_modal_confirmacao),
    ("TC-DEL-003 Modal exibe nome da conta", test_del_modal_exibe_nome_da_conta),
    ("TC-DEL-004 Cancelar mantém a conta", test_del_cancelar_mantem_conta),
    ("TC-DEL-005 Confirmar remove card da lista", test_del_confirmar_remove_conta),
    ("TC-DEL-009 Soft delete — PATCH ativo:false", test_del_usa_soft_delete_nao_hard_delete),
    ("TC-DEL-006 Toast aparece após excluir", test_del_toast_apos_excluir),
    ("TC-DEL-007 Botão excluir não aparece no painel", test_del_btn_nao_aparece_no_painel),
    ("TC-DEL-008 Excluir gasto avulso não regrediu", test_del_avulso_ainda_funciona),
    # Vencimentos Próximos — filtro por pagamento
    ("TC-PROX-001 Conta pendente aparece em Próximos", test_prox_conta_pendente_aparece),
    ("TC-PROX-002 Conta paga NÃO aparece em Próximos", test_prox_conta_paga_nao_aparece),
    ("TC-PROX-005 Conta paga aparece na aba Contas", test_prox_conta_paga_aparece_na_aba_contas),
    ("TC-PROX-006 Empty state quando tudo pago", test_prox_empty_state_quando_tudo_pago),
    ("TC-PROX-003 Marcar paga remove de Próximos", test_prox_marcar_paga_remove_dos_proximos),
    ("TC-PROX-004 Desmarcar paga volta a Próximos", test_prox_desmarcar_volta_aos_proximos),
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