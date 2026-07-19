import asyncio
import os
from playwright.async_api import async_playwright
from backend.ai_service import answer_application_question

PENDING_CONFIRMATIONS = {}

async def auto_apply_job(job_url: str, resume_path: str, model: str, profile_text: str, log_callback, require_confirmation: bool = False, session_id: str = None):
    """
    Automates the LinkedIn Easy Apply flow.
    """
    if "?" in job_url:
        apply_url = f"{job_url}&openSDUIApplyFlow=true"
    else:
        apply_url = f"{job_url}?openSDUIApplyFlow=true"
        
    log_callback("[AUTO-APPLY] Iniciando robô de Candidatura Simplificada...")
    log_callback(f"[AUTO-APPLY] Navegando para a modal: {apply_url}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            state_path = "linkedin_state.json"
            if not os.path.exists(state_path):
                log_callback("[ERRO AUTO-APPLY] linkedin_state.json não encontrado. Faça login primeiro.")
                await browser.close()
                return False
                
            context = await browser.new_context(storage_state=state_path)
            page = await context.new_page()
            
            await page.goto(apply_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(4000)
            
            step = 1
            max_steps = 15
            success = False
            
            while step <= max_steps:
                log_callback(f"[AUTO-APPLY] --- Processando Etapa {step} ---")
                await page.wait_for_timeout(2000)
                
                error_banner = page.locator(".artdeco-inline-feedback--error")
                if await error_banner.count() > 0 and await error_banner.first.is_visible():
                    err_txt = await error_banner.first.inner_text()
                    log_callback(f"[ERRO AUTO-APPLY] O formulário retornou erro: {err_txt}")
                    break
                
                dialog = page.locator("div[role='dialog']")
                if await dialog.count() == 0:
                    log_callback("[AUTO-APPLY] Modal fechada ou processo concluído.")
                    break
                    
                file_inputs = page.locator("input[type='file']")
                count = await file_inputs.count()
                for i in range(count):
                    inp = file_inputs.nth(i)
                    if await inp.is_visible():
                        log_callback(f"[AUTO-APPLY] Fazendo upload do currículo gerado...")
                        await inp.set_input_files(resume_path)
                        await page.wait_for_timeout(1000)
                        
                inputs = page.locator("input:not([type='file']):not([type='hidden']), select, textarea")
                count = await inputs.count()
                
                # Radio button handling groups
                radio_groups = {}
                
                for i in range(count):
                    inp = inputs.nth(i)
                    if not await inp.is_visible():
                        continue
                        
                    tag_name = await inp.evaluate("el => el.tagName.toLowerCase()")
                    type_attr = await inp.get_attribute("type") or "text"
                    id_attr = await inp.get_attribute("id")
                    name_attr = await inp.get_attribute("name")
                    
                    label_text = "Desconhecido"
                    if id_attr:
                        label = page.locator(f"label[for='{id_attr}']")
                        if await label.count() > 0:
                            label_text = await label.first.inner_text()
                            
                    value = await inp.evaluate("el => el.value")
                    if value and type_attr not in ["checkbox", "radio"]:
                        continue
                        
                    if type_attr == "radio":
                        if name_attr:
                            if name_attr not in radio_groups:
                                radio_groups[name_attr] = {"question": "Escolha uma opção", "options": [], "locators": []}
                            radio_groups[name_attr]["options"].append(label_text)
                            radio_groups[name_attr]["locators"].append(inp)
                            
                        # If a radio is not grouped by name (rare), we ignore it or just click the first
                        continue
                            
                    elif tag_name == "select":
                        options = await inp.locator("option").all_inner_texts()
                        if len(options) > 1:
                            clean_options = [opt.strip() for opt in options if opt.strip() and opt.strip().lower() != "selecionar"]
                            if clean_options:
                                log_callback(f"[AUTO-APPLY] IA pensando na pergunta (Dropdown): {label_text}...")
                                answer = await answer_application_question(model, label_text, "select", profile_text, clean_options)
                                log_callback(f"[AUTO-APPLY] Resposta da IA: {answer}")
                                try:
                                    await inp.select_option(label=answer)
                                except:
                                    try:
                                        await inp.select_option(clean_options[0])
                                    except:
                                        pass
                                
                    elif type_attr == "checkbox":
                        is_checked = await inp.evaluate("el => el.checked")
                        if not is_checked:
                            await inp.click(force=True)
                            
                    else:
                        log_callback(f"[AUTO-APPLY] IA pensando na pergunta (Texto): {label_text}...")
                        answer = await answer_application_question(model, label_text, type_attr, profile_text)
                        log_callback(f"[AUTO-APPLY] Resposta da IA: {answer}")
                        await inp.fill(answer)
                
                # Handle radio groups
                for group_name, group_data in radio_groups.items():
                    options = group_data["options"]
                    locators = group_data["locators"]
                    
                    # See if any is checked
                    any_checked = False
                    for loc in locators:
                        if await loc.evaluate("el => el.checked"):
                            any_checked = True
                            break
                            
                    if not any_checked and options:
                        # Usually the "question" for a radio group is inside a fieldset legend or a preceding h3.
                        # For simplicity, we just pass the options to AI and ask it to pick the best.
                        log_callback(f"[AUTO-APPLY] IA pensando na escolha (Radio): Opções {options}...")
                        answer = await answer_application_question(model, "Selecione a melhor opção", "radio", profile_text, options)
                        log_callback(f"[AUTO-APPLY] Resposta da IA: {answer}")
                        
                        # Find the index of the answer in options
                        best_idx = 0
                        for idx, opt in enumerate(options):
                            if answer.lower() in opt.lower():
                                best_idx = idx
                                break
                        await locators[best_idx].click(force=True)
                        
                btn_next = page.locator("button[aria-label*='Avançar' i], button[aria-label*='Next' i], button:has-text('Avançar'), button:has-text('Revisar'), button:has-text('Review')").first
                btn_submit = page.locator("button[aria-label*='Enviar' i], button[aria-label*='Submit' i], button:has-text('Enviar candidatura')").first
                
                if await btn_submit.count() > 0 and await btn_submit.is_visible():
                    if require_confirmation and session_id:
                        log_callback(f"[ACTION_REQUIRED:{session_id}] Formulário preenchido. Aguardando sua confirmação para enviar...")
                        event = asyncio.Event()
                        PENDING_CONFIRMATIONS[session_id] = event
                        
                        # Wait until the frontend hits the confirm API
                        await event.wait()
                        
                        if session_id in PENDING_CONFIRMATIONS:
                            del PENDING_CONFIRMATIONS[session_id]
                            
                        log_callback("[AUTO-APPLY] Confirmação recebida! Clicando em ENVIAR...")
                    else:
                        log_callback("[AUTO-APPLY] Botão ENVIAR encontrado! Clicando...")
                        
                    await btn_submit.click()
                    await page.wait_for_timeout(3000)
                    success = True
                    step += 1
                elif await btn_next.count() > 0 and await btn_next.is_visible():
                    log_callback("[AUTO-APPLY] Avançando para próxima etapa...")
                    await btn_next.click()
                    step += 1
                else:
                    log_callback("[AUTO-APPLY] Nenhum botão de Avançar/Enviar encontrado. O fluxo pode ter travado.")
                    break
                    
            await browser.close()
            return success
            
    except Exception as e:
        log_callback(f"[ERRO AUTO-APPLY] {str(e)}")
        return False
