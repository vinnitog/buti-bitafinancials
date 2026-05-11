"""
Playwright E2E Tests — Buti & Bita Financials
Simula um usuário real interagindo com o app no browser.

Cobertura:
  - Smoke: carregamento, header, abas, navegação
  - Dashboard: salário, progress bar, cards de resumo
  - Navegação: todas as 6 abas funcionam
  - +Novo / Sub-abas: troca entre sub-abas, formulários visíveis
  - Identificação: Buti/Bita com cores corretas
  - Tema: toggle yin yang muda a cor de fundo
  - Formulário de conta: campos, validação nome obrigatório
  - Checkbox "já paga": aparece ao digitar dia passado
  - Fechar mês: modal com campo de confirmação
  - Fechar mês: texto errado é bloqueado
  - Modal de extrato: abre e fecha corretamente

Observação: testes que dependem do Supabase são mockados via route interception.
"""

import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect, Page, Browser

APP_PATH = "file:///C:/Users/Togszera/Desktop/APP - Controle Finanças/index.html"
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m~\033[0m"

results = []

def run_test(name: str, fn, page: Page):
    try:
        fn(page)
        results.append(("PASS", name))
        print(f"  {PASS} {name}")
    except Exception as e:
        msg = str(e).split("\n")[0][:120]
        results.append(("FAIL", name, msg))
        print(f"  {FAIL} {name}")
        print(f"      → {msg}")

def mock_supabase(page: Page):
    """Intercepta todas as chamadas ao Supabase e retorna dados mock."""
    contas_mock = [
        {"id": 1, "nome": "Carro", "emoji": "🚗", "valor": 2600, "dia": 10,
         "cat": "financiamento", "tipo": "manual", "obs": "conta mais cara", "ativo": True},
        {"id": 2, "nome": "Seguro do Carro", "emoji": "🛡️", "valor": 240, "dia": 0,
         "cat": "fixa", "tipo": "auto", "obs": "débito automático", "ativo": True},
        {"id": 3, "nome": "Spotify", "emoji": "🎵", "valor": 22, "dia": 0,
         "cat": "assinatura", "tipo": "auto", "obs": "", "ativo": True},
    ]
    pagamentos_mock = [
        {"id": 10, "conta_id": 1, "nome": "Carro", "emoji": "🚗", "valor": 2600,
         "cat": "financiamento", "tipo": "manual", "obs": "", "dia": 10,
         "mes": 5, "ano": 2026, "pago": False, "pago_em": None, "pago_por": ""},
        {"id": 11, "conta_id": 2, "nome": "Seguro do Carro", "emoji": "🛡️", "valor": 240,
         "cat": "fixa", "tipo": "auto", "obs": "", "dia": 0,
         "mes": 5, "ano": 2026, "pago": True, "pago_em": "2026-05-01T00:00:00Z", "pago_por": "auto"},
        {"id": 12, "conta_id": 3, "nome": "Spotify", "emoji": "🎵", "valor": 22,
         "cat": "assinatura", "tipo": "auto", "obs": "", "dia": 0,
         "mes": 5, "ano": 2026, "pago": True, "pago_em": "2026-05-01T00:00:00Z", "pago_por": "auto"},
    ]
    config_salarios = {"buti": {"base": 12000, "bonus": 1000}, "bita": {"base": 3000, "bonus": 500}}

    def handle_route(route):
        url = route.request.url
        method = route.request.method

        if "supabase.co" not in url:
            route.continue_()
            return

        # POST para contas/pagamentos — retornar objeto criado
        if method == "POST":
            route.fulfill(status=201, content_type="application/json", body='[{"id":99}]')
            return

        # PATCH / DELETE — sucesso silencioso
        if method in ("PATCH", "DELETE"):
            route.fulfill(status=200, content_type="application/json", body='[]')
            return

        # GET — rotear por tabela
        if "contas" in url and "configuracoes" not in url:
            import json
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(contas_mock))
        elif "pagamentos" in url:
            import json
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps(pagamentos_mock))
        elif "gastos_avulsos" in url:
            route.fulfill(status=200, content_type="application/json", body='[]')
        elif "configuracoes" in url:
            import json
            if "chave=eq.salarios" in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps([{"chave": "salarios", "valor": config_salarios}]))
            elif "chave=eq.variaveis" in url:
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps([{"chave": "variaveis", "valor": []}]))
            else:
                route.fulfill(status=200, content_type="application/json", body='[]')
        else:
            route.fulfill(status=200, content_type="application/json", body='[]')

    page.route("**/*", handle_route)


def load_app(page: Page):
    """Carrega o app com mocks ativos e aguarda inicialização."""
    mock_supabase(page)
    page.goto(APP_PATH, wait_until="domcontentloaded")
    # Aguarda o header aparecer (confirma que o JS rodou)
    page.wait_for_selector(".header", timeout=8000)
    page.wait_for_timeout(800)  # aguarda async init completar


# ═══════════════════════════════════════════════
# SMOKE TESTS
# ═══════════════════════════════════════════════

def test_smoke_titulo(page):
    """TC-SMK-001 Título da página está correto."""
    assert page.title() == "Buti & Bita Financials"

def test_smoke_header_nome(page):
    """TC-SMK-001 Header exibe Buti & Bita Financials."""
    header = page.locator(".app-name").inner_text()
    assert "Buti" in header
    assert "Bita" in header
    assert "Financials" in header

def test_smoke_seis_abas(page):
    """TC-SMK-003 Seis abas de navegação estão visíveis."""
    abas = page.locator(".nav-btn").all()
    assert len(abas) == 6

def test_smoke_dashboard_ativo(page):
    """TC-SMK-002 Dashboard é a seção ativa ao carregar."""
    dashboard = page.locator("#section-dashboard")
    assert "active" in dashboard.get_attribute("class")

def test_smoke_sync_status(page):
    """TC-SMK-004 Status de sincronização aparece no header."""
    sub = page.locator(".header-sub").inner_text()
    # Deve mostrar algum estado (conectando, sincronizado, erro, etc)
    assert len(sub.strip()) > 0

# ═══════════════════════════════════════════════
# NAVEGAÇÃO
# ═══════════════════════════════════════════════

def test_nav_contas(page):
    """TC-UI-SMK-003 Clicar em Contas abre a seção de contas."""
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(300)
    assert "active" in page.locator("#section-contas").get_attribute("class")

def test_nav_gastos(page):
    """TC-UI-SMK-003 Clicar em Gastos abre a seção de gastos."""
    page.locator(".nav-btn").nth(2).click()
    page.wait_for_timeout(300)
    assert "active" in page.locator("#section-gastos").get_attribute("class")

def test_nav_novo(page):
    """TC-UI-SMK-003 Clicar em +Novo abre a seção de cadastro."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(300)
    assert "active" in page.locator("#section-cadastrar").get_attribute("class")

def test_nav_historico(page):
    """TC-UI-SMK-003 Clicar em Histórico abre a seção correta."""
    page.locator(".nav-btn").nth(4).click()
    page.wait_for_timeout(300)
    assert "active" in page.locator("#section-historico").get_attribute("class")

def test_nav_config(page):
    """TC-UI-SMK-003 Clicar em Configuração abre a seção correta."""
    page.locator(".nav-btn").nth(5).click()
    page.wait_for_timeout(300)
    assert "active" in page.locator("#section-config").get_attribute("class")

def test_nav_volta_dashboard(page):
    """TC-UI-SMK-003 Após navegar, volta ao Painel corretamente."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    page.locator(".nav-btn").nth(0).click()
    page.wait_for_timeout(200)
    assert "active" in page.locator("#section-dashboard").get_attribute("class")

# ═══════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════

def test_dashboard_salary_cards(page):
    """TC-UI Dashboard exibe dois cards de salário (Buti e Bita)."""
    buti = page.locator("#salary-buti-base").inner_text()
    bita = page.locator("#salary-bita-base").inner_text()
    # Com os mocks, os valores devem estar preenchidos
    assert len(buti) > 0
    assert len(bita) > 0

def test_dashboard_salary_total_visible(page):
    """TC-UI Renda total do casal está visível no painel."""
    page.locator(".nav-btn").nth(0).click()
    page.wait_for_timeout(300)
    page.wait_for_selector(".salary-total-bar", timeout=5000)
    total_bar = page.locator(".salary-total-bar")
    assert total_bar.count() == 1, "salary-total-bar não encontrado"
    assert total_bar.is_visible(), "salary-total-bar não está visível"
    html = page.locator(".salary-total-bar").inner_text()
    assert "renda total" in html.lower(), f"Texto 'Renda total' não encontrado: '{html}'"

def test_dashboard_summary_cards(page):
    """TC-UI Quatro cards de resumo aparecem no dashboard."""
    # Usar seletor específico para o dashboard
    cards = page.locator("#section-dashboard .summary-grid .sum-card").all()
    assert len(cards) == 4, f"Esperado 4 cards no dashboard, encontrado {len(cards)}"

def test_dashboard_progress_bar(page):
    """TC-UI Barra de progresso está visível."""
    assert page.locator(".progress-wrap").is_visible()
    assert page.locator(".progress-bar").is_visible()

def test_dashboard_proximos_vencimentos(page):
    """TC-UI-016 Seção de vencimentos próximos está presente."""
    assert page.locator("#proximos-list").is_visible()

# ═══════════════════════════════════════════════
# TEMA
# ═══════════════════════════════════════════════

def test_tema_toggle_existe(page):
    """TC-UI-011 Botão yin yang de troca de tema está no header."""
    toggle = page.locator(".theme-toggle")
    assert toggle.is_visible()

def test_tema_svg_yin_yang(page):
    """TC-UI-011 SVG do yin yang contém as duas cores."""
    svg_html = page.locator(".theme-toggle svg").inner_html()
    assert "#4ade80" in svg_html  # verde
    assert "#c084fc" in svg_html  # roxo

def test_tema_troca_para_roxo(page):
    """TC-UI-011 Clicar no toggle muda o tema para roxo."""
    # Captura background antes
    bg_antes = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.locator(".theme-toggle").click()
    page.wait_for_timeout(400)
    bg_depois = page.evaluate("getComputedStyle(document.body).backgroundColor")
    # Background deve mudar (temas têm cores de fundo diferentes)
    assert bg_antes != bg_depois, "Background não mudou após toggle de tema"

def test_tema_toggle_volta_oliva(page):
    """TC-UI-011 Segundo clique restaura o tema oliva."""
    page.locator(".theme-toggle").click()
    page.wait_for_timeout(300)
    bg_roxo = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.locator(".theme-toggle").click()
    page.wait_for_timeout(300)
    bg_oliva = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert bg_roxo != bg_oliva, "Segundo clique não restaurou o tema"

# ═══════════════════════════════════════════════
# IDENTIFICAÇÃO BUTI / BITA
# ═══════════════════════════════════════════════

def test_buti_bita_botoes_visiveis(page):
    """TC-UI-012 Botões Buti e Bita estão visíveis na aba +Novo."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(300)
    assert page.locator("#pessoa-btn-eu").is_visible()
    assert page.locator("#pessoa-btn-esposa").is_visible()

def test_buti_label_correto(page):
    """TC-UI-012 Botão exibe 'Buti' sem emojis."""
    page.locator(".nav-btn").nth(3).click()
    text = page.locator("#pessoa-btn-eu").inner_text()
    assert text.strip() == "Buti"

def test_bita_label_correto(page):
    """TC-UI-012 Botão exibe 'Bita' sem emojis."""
    page.locator(".nav-btn").nth(3).click()
    text = page.locator("#pessoa-btn-esposa").inner_text()
    assert text.strip() == "Bita"

def test_buti_ativo_por_padrao(page):
    """TC-UI-012 Buti está ativo por padrão."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    cls = page.locator("#pessoa-btn-eu").get_attribute("class")
    assert "active" in cls

def test_bita_fica_ativo_ao_clicar(page):
    """TC-UI-012 Clicar em Bita marca ela como ativa."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    page.locator("#pessoa-btn-esposa").click()
    page.wait_for_timeout(200)
    cls_bita = page.locator("#pessoa-btn-esposa").get_attribute("class")
    cls_buti = page.locator("#pessoa-btn-eu").get_attribute("class")
    assert "active" in cls_bita
    assert "active" not in cls_buti

# ═══════════════════════════════════════════════
# SUB-ABAS EM +NOVO
# ═══════════════════════════════════════════════

def test_subabas_existem(page):
    """TC-UI Quatro sub-abas estão visíveis em +Novo."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    sub_btns = page.locator(".sub-btn").all()
    assert len(sub_btns) == 4

def test_subaba_conta_ativa_por_padrao(page):
    """TC-UI Sub-aba Conta está ativa ao entrar em +Novo."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    cls = page.locator("#subbtn-conta").get_attribute("class")
    assert "active" in cls
    assert page.locator("#subtab-conta").is_visible()

def test_subaba_gasto_abre(page):
    """TC-UI Clicar em 'Gasto avulso' mostra o formulário correto."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    page.locator("#subbtn-gasto").click()
    page.wait_for_timeout(200)
    assert page.locator("#subtab-gasto").is_visible()
    assert page.locator("#subtab-conta").is_hidden()

def test_subaba_salario_abre(page):
    """TC-UI Clicar em 'Salários' mostra formulário de salários."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    page.locator("#subbtn-salario").click()
    page.wait_for_timeout(200)
    assert page.locator("#subtab-salario").is_visible()
    assert page.locator("#sal-buti-base").is_visible()
    assert page.locator("#sal-bita-base").is_visible()

def test_subaba_import_abre(page):
    """TC-UI Clicar em 'Importar' mostra área de upload."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    page.locator("#subbtn-import").click()
    page.wait_for_timeout(200)
    assert page.locator("#subtab-import").is_visible()
    assert page.locator(".upload-area").is_visible()

# ═══════════════════════════════════════════════
# FORMULÁRIO DE NOVA CONTA
# ═══════════════════════════════════════════════

def test_form_campos_visiveis(page):
    """TC-UI Campos do formulário de nova conta estão visíveis."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    assert page.locator("#new-name").is_visible()
    assert page.locator("#new-valor").is_visible()
    assert page.locator("#new-dia").is_visible()
    assert page.locator("#new-cat").is_visible()

def test_form_validacao_nome_obrigatorio(page):
    """TC-UI-020 Salvar sem nome exibe toast de erro."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    # Não preenche nome, clica em cadastrar
    page.locator("#btn-add-conta").click()
    page.wait_for_timeout(500)
    toast = page.locator(".toast")
    assert toast.is_visible()
    assert "nome" in toast.inner_text().lower() or "informe" in toast.inner_text().lower()

def test_form_checkbox_oculto_por_padrao(page):
    """TC-UI-019 Checkbox 'já paga' está oculto inicialmente."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    wrap = page.locator("#new-ja-pago-wrap")
    # Deve estar oculto (display:none)
    display = page.evaluate("document.getElementById('new-ja-pago-wrap').style.display")
    assert display == "none" or not wrap.is_visible()

def test_form_checkbox_aparece_dia_passado(page):
    """TC-UI-019 Checkbox 'já paga' aparece ao digitar dia que já passou."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    # Dia 1 certamente já passou em maio de 2026
    page.locator("#new-dia").fill("1")
    page.locator("#new-dia").dispatch_event("input")
    page.wait_for_timeout(300)
    display = page.evaluate("document.getElementById('new-ja-pago-wrap').style.display")
    assert display == "block", f"Esperado 'block', obtido '{display}'"

def test_form_checkbox_oculta_dia_futuro(page):
    """TC-UI-019 Checkbox 'já paga' fica oculto para dia futuro."""
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    # Dia 31 é no futuro em relação a qualquer dia atual
    page.locator("#new-dia").fill("31")
    page.locator("#new-dia").dispatch_event("input")
    page.wait_for_timeout(300)
    display = page.evaluate("document.getElementById('new-ja-pago-wrap').style.display")
    assert display == "none", f"Esperado 'none', obtido '{display}'"

# ═══════════════════════════════════════════════
# FECHAR MÊS — MODAL DE CONFIRMAÇÃO
# ═══════════════════════════════════════════════

def _click_fechar_mes(page):
    """Helper: navega para Config e clica no botão correto de fechar mês."""
    page.locator(".nav-btn").nth(5).click()
    page.wait_for_timeout(200)
    # Usa texto exato para evitar conflito com o btn-danger do modal de confirmação
    page.locator("button.btn-danger", has_text="Fechar mês").click()
    page.wait_for_timeout(400)

def test_fechar_mes_abre_modal(page):
    """TC-UI-013 Clicar em 'Fechar mês' abre modal de confirmação."""
    _click_fechar_mes(page)
    overlay = page.locator("#confirm-overlay")
    cls = overlay.get_attribute("class")
    assert "hidden" not in cls, "Modal de confirmação não abriu"

def test_fechar_mes_campo_digitacao_visivel(page):
    """TC-UI-013 Modal exibe campo para digitar palavra de confirmação."""
    _click_fechar_mes(page)
    wrap = page.locator("#confirm-type-wrap")
    assert wrap.is_visible()
    assert page.locator("#confirm-type-input").is_visible()

def test_fechar_mes_palavra_errada_bloqueia(page):
    """TC-UI-014 Digitar palavra errada exibe toast e não fecha modal."""
    _click_fechar_mes(page)
    page.locator("#confirm-type-input").fill("errado")
    page.locator("#confirm-ok-btn").click()
    page.wait_for_timeout(400)
    cls = page.locator("#confirm-overlay").get_attribute("class")
    assert "hidden" not in cls, "Modal fechou com palavra errada — bug!"
    toast = page.locator(".toast")
    assert toast.is_visible()

def test_fechar_mes_palavra_correta_funciona(page):
    """TC-UI-014 Digitar FECHAR executa e fecha o modal."""
    _click_fechar_mes(page)
    page.locator("#confirm-type-input").fill("FECHAR")
    page.locator("#confirm-ok-btn").click()
    page.wait_for_timeout(500)
    cls = page.locator("#confirm-overlay").get_attribute("class")
    assert "hidden" in cls, "Modal não fechou com palavra correta"

def test_fechar_mes_minusculo_aceito(page):
    """TC-UI-014 'fechar' minúsculo também é aceito (case-insensitive)."""
    _click_fechar_mes(page)
    page.locator("#confirm-type-input").fill("fechar")
    page.locator("#confirm-ok-btn").click()
    page.wait_for_timeout(500)
    cls = page.locator("#confirm-overlay").get_attribute("class")
    assert "hidden" in cls, "Case-insensitive falhou"

def test_fechar_mes_cancelar_fecha_modal(page):
    """TC-UI-013 Clicar em Cancelar fecha o modal sem executar ação."""
    _click_fechar_mes(page)
    page.locator("#confirm-overlay .btn-secondary").click()
    page.wait_for_timeout(300)
    cls = page.locator("#confirm-overlay").get_attribute("class")
    assert "hidden" in cls, "Modal não fechou ao cancelar"

# ═══════════════════════════════════════════════
# MODAL DE EXTRATO (Histórico)
# ═══════════════════════════════════════════════

def test_modal_extrato_existe(page):
    """TC-UI-018 Modal de extrato existe no DOM e começa oculto."""
    overlay = page.locator("#modal-overlay")
    assert overlay.count() == 1
    cls = overlay.get_attribute("class")
    assert "hidden" in cls

def test_modal_fechar_botao_x(page):
    """TC-UI-018 Botão ✕ fecha o modal de extrato."""
    # Abrir o modal via JS diretamente
    page.evaluate("document.getElementById('modal-overlay').classList.remove('hidden')")
    page.wait_for_timeout(200)
    page.locator(".modal-close").first.click()
    page.wait_for_timeout(300)
    cls = page.locator("#modal-overlay").get_attribute("class")
    assert "hidden" in cls

def test_modal_fechar_clique_overlay(page):
    """TC-UI-018 Clicar no overlay escuro fecha o modal."""
    page.evaluate("document.getElementById('modal-overlay').classList.remove('hidden')")
    page.wait_for_timeout(200)
    # Clica no canto superior esquerdo do overlay (fora do modal)
    overlay = page.locator("#modal-overlay")
    overlay.click(position={"x": 10, "y": 10})
    page.wait_for_timeout(300)
    cls = page.locator("#modal-overlay").get_attribute("class")
    assert "hidden" in cls

# ═══════════════════════════════════════════════
# ALERTA BADGE → NAVEGA PARA PAINEL
# ═══════════════════════════════════════════════

def test_badge_alerta_navega_para_painel(page):
    """TC-UI-017 Clicar no badge de alertas leva ao painel."""
    # Primeiro, ir para outra aba
    page.locator(".nav-btn").nth(3).click()
    page.wait_for_timeout(200)
    assert "active" not in page.locator("#section-dashboard").get_attribute("class")

    # Forçar badge visível
    page.evaluate("""
        const badge = document.getElementById('alert-count');
        badge.style.display = 'block';
        badge.textContent = '⚠ 1 alerta';
    """)
    page.locator("#alert-count").click()
    page.wait_for_timeout(300)
    assert "active" in page.locator("#section-dashboard").get_attribute("class")

# ═══════════════════════════════════════════════
# CONTAS — CARDS RENDERIZADOS
# ═══════════════════════════════════════════════

def test_contas_lista_financiamentos(page):
    """TC-UI Aba Contas renderiza lista de financiamentos."""
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(600)
    lista = page.locator("#list-financiamentos")
    assert lista.is_visible()
    # Com os mocks, deve ter pelo menos 1 card
    cards = lista.locator(".bill-card").all()
    assert len(cards) >= 1, "Nenhum card de financiamento renderizado"

def test_contas_card_tem_nome_e_valor(page):
    """TC-UI Cards de conta exibem nome e valor."""
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(600)
    primeiro_card = page.locator("#list-financiamentos .bill-card").first
    nome = primeiro_card.locator(".bill-name").inner_text()
    valor = primeiro_card.locator(".bill-amount").inner_text()
    assert len(nome) > 0
    assert "R$" in valor

def test_contas_auto_tem_tag(page):
    """TC-UI Cards de débito automático exibem tag AUTO."""
    page.locator(".nav-btn").nth(1).click()
    page.wait_for_timeout(600)
    auto_cards = page.locator(".tag-auto").all()
    assert len(auto_cards) >= 1, "Nenhuma tag AUTO encontrada"


# ═══════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════

TESTS = [
    # Smoke
    ("TC-SMK-001 Título da página", test_smoke_titulo),
    ("TC-SMK-001 Header exibe Buti & Bita Financials", test_smoke_header_nome),
    ("TC-SMK-003 Seis abas de navegação visíveis", test_smoke_seis_abas),
    ("TC-SMK-002 Dashboard ativo ao carregar", test_smoke_dashboard_ativo),
    ("TC-SMK-004 Status de sincronização no header", test_smoke_sync_status),
    # Navegação
    ("TC-UI Navega para Contas", test_nav_contas),
    ("TC-UI Navega para Gastos", test_nav_gastos),
    ("TC-UI Navega para +Novo", test_nav_novo),
    ("TC-UI Navega para Histórico", test_nav_historico),
    ("TC-UI Navega para Configuração", test_nav_config),
    ("TC-UI Volta ao Painel após navegar", test_nav_volta_dashboard),
    # Dashboard
    ("TC-UI Cards de salário Buti e Bita visíveis", test_dashboard_salary_cards),
    ("TC-UI Barra 'Renda total do casal' visível", test_dashboard_salary_total_visible),
    ("TC-UI Quatro cards de resumo no dashboard", test_dashboard_summary_cards),
    ("TC-UI Barra de progresso visível", test_dashboard_progress_bar),
    ("TC-UI-016 Seção vencimentos próximos existe", test_dashboard_proximos_vencimentos),
    # Tema
    ("TC-UI-011 Botão yin yang existe", test_tema_toggle_existe),
    ("TC-UI-011 SVG contém cores verde e roxa", test_tema_svg_yin_yang),
    ("TC-UI-011 Toggle muda background para roxo", test_tema_troca_para_roxo),
    ("TC-UI-011 Segundo toggle restaura tema oliva", test_tema_toggle_volta_oliva),
    # Identificação
    ("TC-UI-012 Botões Buti e Bita visíveis", test_buti_bita_botoes_visiveis),
    ("TC-UI-012 Botão exibe 'Buti' sem emojis", test_buti_label_correto),
    ("TC-UI-012 Botão exibe 'Bita' sem emojis", test_bita_label_correto),
    ("TC-UI-012 Buti ativo por padrão", test_buti_ativo_por_padrao),
    ("TC-UI-012 Clicar em Bita a ativa", test_bita_fica_ativo_ao_clicar),
    # Sub-abas
    ("TC-UI Quatro sub-abas em +Novo", test_subabas_existem),
    ("TC-UI Sub-aba Conta ativa por padrão", test_subaba_conta_ativa_por_padrao),
    ("TC-UI Sub-aba Gasto avulso abre", test_subaba_gasto_abre),
    ("TC-UI Sub-aba Salários abre com campos", test_subaba_salario_abre),
    ("TC-UI Sub-aba Importar exibe upload", test_subaba_import_abre),
    # Formulário
    ("TC-UI Campos do form de conta visíveis", test_form_campos_visiveis),
    ("TC-UI-020 Sem nome exibe erro", test_form_validacao_nome_obrigatorio),
    ("TC-UI-019 Checkbox 'já paga' oculto por padrão", test_form_checkbox_oculto_por_padrao),
    ("TC-UI-019 Checkbox aparece para dia passado", test_form_checkbox_aparece_dia_passado),
    ("TC-UI-019 Checkbox oculto para dia futuro", test_form_checkbox_oculta_dia_futuro),
    # Fechar mês
    ("TC-UI-013 Fechar mês abre modal", test_fechar_mes_abre_modal),
    ("TC-UI-013 Modal exibe campo para digitar", test_fechar_mes_campo_digitacao_visivel),
    ("TC-UI-014 Palavra errada bloqueia execução", test_fechar_mes_palavra_errada_bloqueia),
    ("TC-UI-014 'FECHAR' executa e fecha modal", test_fechar_mes_palavra_correta_funciona),
    ("TC-UI-014 'fechar' minúsculo é aceito", test_fechar_mes_minusculo_aceito),
    ("TC-UI-013 Cancelar fecha o modal", test_fechar_mes_cancelar_fecha_modal),
    # Modal extrato
    ("TC-UI-018 Modal de extrato começa oculto", test_modal_extrato_existe),
    ("TC-UI-018 Botão ✕ fecha o modal", test_modal_fechar_botao_x),
    ("TC-UI-018 Clique no overlay fecha o modal", test_modal_fechar_clique_overlay),
    # Badge alertas
    ("TC-UI-017 Badge alerta navega para painel", test_badge_alerta_navega_para_painel),
    # Contas
    ("TC-UI Aba Contas renderiza financiamentos", test_contas_lista_financiamentos),
    ("TC-UI Cards exibem nome e valor", test_contas_card_tem_nome_e_valor),
    ("TC-UI Cards de débito auto têm tag AUTO", test_contas_auto_tem_tag),
]


def main():
    print("\n" + "═" * 60)
    print("  Playwright E2E — Buti & Bita Financials")
    print("  Browser: Chromium (headless)")
    print("  Supabase: mockado (sem chamadas reais)")
    print("═" * 60 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        #browser = p.chromium.launch(headless=False, slow_mo=600)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},  # iPhone 14
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
        )

        total = len(TESTS)
        suite_groups = {
            "SMOKE": [],
            "NAVEGAÇÃO": [],
            "DASHBOARD": [],
            "TEMA": [],
            "IDENTIFICAÇÃO": [],
            "SUB-ABAS": [],
            "FORMULÁRIO": [],
            "FECHAR MÊS": [],
            "MODAL EXTRATO": [],
            "BADGE ALERTAS": [],
            "CONTAS": [],
        }

        def get_group(name):
            if "SMK" in name: return "SMOKE"
            if "Navega" in name or "Volta" in name: return "NAVEGAÇÃO"
            if "dashboard" in name.lower() or "Dashboard" in name or "salário" in name.lower() or "Saldo" in name or "Renda" in name or "progress" in name.lower() or "vencimento" in name.lower(): return "DASHBOARD"
            if "tema" in name.lower() or "yin" in name.lower() or "toggle" in name.lower() or "background" in name.lower() or "roxo" in name.lower() or "oliva" in name.lower() or "UI-011" in name: return "TEMA"
            if "Buti" in name or "Bita" in name or "UI-012" in name: return "IDENTIFICAÇÃO"
            if "sub-aba" in name.lower() or "Sub-aba" in name or "sub" in name.lower(): return "SUB-ABAS"
            if "Campos" in name or "form" in name.lower() or "UI-020" in name or "UI-019" in name or "checkbox" in name.lower(): return "FORMULÁRIO"
            if "Fechar" in name or "UI-013" in name or "UI-014" in name or "palavra" in name.lower(): return "FECHAR MÊS"
            if "extrato" in name.lower() or "UI-018" in name or "overlay" in name.lower(): return "MODAL EXTRATO"
            if "badge" in name.lower() or "UI-017" in name: return "BADGE ALERTAS"
            if "Contas" in name or "financiamento" in name.lower() or "AUTO" in name: return "CONTAS"
            return "OUTROS"

        for test_name, test_fn in TESTS:
            page = context.new_page()
            # Suprimir erros de console (supabase, etc)
            page.on("console", lambda m: None)
            page.on("pageerror", lambda e: None)
            load_app(page)
            group = get_group(test_name)
            run_test(test_name, test_fn, page)
            page.close()

        browser.close()

    # Relatório final
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    rate = round((passed / total) * 100) if total > 0 else 0

    print("\n" + "═" * 60)
    print(f"  RESULTADO: {passed}/{total} passou ({rate}%)")
    if failed > 0:
        print(f"\n  Falhas ({failed}):")
        for r in results:
            if r[0] == "FAIL":
                print(f"    {FAIL} {r[1]}")
                if len(r) > 2:
                    print(f"       {r[2]}")
    print("═" * 60 + "\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
