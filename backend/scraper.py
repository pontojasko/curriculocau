from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os
import urllib.parse
import json

CDP_URL = os.environ.get("OBSCURA_CDP_URL", "ws://127.0.0.1:9223")

async def scrape_job_url(url: str):
    async with async_playwright() as p:
        try:
            # Connect to Obscura CDP
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to the URL
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # Small delay for JS to render
            await page.wait_for_timeout(3000)
            
            # Get content and title
            content = await page.content()
            title = await page.title()
            
            await browser.close()
        except Exception as e:
            return {"error": str(e)}
        
        # Extract text with BeautifulSoup
        soup = BeautifulSoup(content, 'lxml')
        
        # Remove noisy tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.extract()
            
        # LinkedIn specific fallback if needed
        desc_div = None
        if "linkedin.com/jobs" in url:
            desc_div = soup.find("div", class_="show-more-less-html__markup")
        elif "gupy.io" in url:
            desc_div = soup.find("div", {"data-testid": "job-description"}) or soup.find("div", class_="description")

        if desc_div:
            text = desc_div.get_text(separator="\n", strip=True)
        else:
            # Fallback: get text from body
            body = soup.find("body")
            if body:
                text = body.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
                
        # Clean up excessive newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)
            
        # Detect apply type
        apply_type = "external"
        apply_platform = "other"
        
        # Look for buttons or links indicating Easy Apply
        apply_btn = soup.find(class_=lambda x: x and "jobs-apply-button" in x)
        if apply_btn:
            apply_type = "easy_apply"
        else:
            for el in soup.find_all(['button', 'a']):
                text = el.get_text(strip=True).lower()
                if "candidatura simplificada" in text or "easy apply" in text:
                    apply_type = "easy_apply"
                    break
                elif text == "candidatar-se" or text == "apply":
                    apply_type = "external"
                    if el.name == 'a':
                        href = el.get("href", "").lower()
                        if "inhire" in href:
                            apply_platform = "inhire"
                    break

        if apply_type == "external":
            lower_content = content.lower()
            if "candidatura simplificada" in lower_content or "easy apply" in lower_content:
                apply_type = "easy_apply"
                
        return {
            "title": title,
            "description": clean_text,
            "apply_type": apply_type,
            "apply_platform": apply_platform
        }

async def _internal_search_posts(keywords, processed_ids, p):
    url = f"https://www.linkedin.com/search/results/content/?keywords={urllib.parse.quote(keywords)}&origin=FACETED_SEARCH"
    try:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        await browser.close()
    except Exception as e:
        return
        
    soup = BeautifulSoup(content, 'lxml')
    posts = soup.find_all("div", class_=lambda x: x and "feed-shared-update-v2" in x)
    
    yielded_count = 0
    for post in posts:
        if yielded_count >= 5:
            break
        try:
            author_el = post.find("span", class_=lambda x: x and "update-components-actor__title" in x) or \
                        post.find("span", class_=lambda x: x and "feed-shared-actor__title" in x)
            author = author_el.get_text(strip=True).split('\n')[0] if author_el else "Autor Desconhecido"
            
            title = f"Post de {author}"
            company = title
            
            link_el = post.find("a", href=lambda h: h and ("/posts/" in h or "/feed/update/" in h))
            if not link_el:
                continue
                
            href = link_el.get("href", "")
            clean_url = href.split('?')[0]
            
            job_id = clean_url.split('/')[-1] if not clean_url.endswith('/') else clean_url.split('/')[-2]
            
            if job_id not in processed_ids:
                job_obj = {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": "Post (Remoto)",
                    "url": clean_url
                }
                import asyncio
                await asyncio.sleep(0.3)
                yield json.dumps(job_obj) + "\n"
                yielded_count += 1
        except Exception:
            continue

async def search_linkedin_jobs(keywords: str, negative_keywords: str = "", location: str = "Brasil", remote_only: bool = False):
    if location.strip().lower() == "brasil":
        location = "Brazil"
        
    if negative_keywords:
        neg_words = [w.strip() for w in negative_keywords.split(',') if w.strip()]
        if neg_words:
            neg_query = " ".join([f'NOT "{w}"' for w in neg_words])
            keywords = f"({keywords}) {neg_query}"
            
    if remote_only:
        keywords = f"({keywords}) AND (Remoto OR Remote OR \"Home Office\")"
        
    encoded_keywords = urllib.parse.quote(keywords)
    encoded_location = urllib.parse.quote(location)
    url = f"https://www.linkedin.com/jobs/search?keywords={encoded_keywords}&location={encoded_location}"
    if remote_only:
        url += "&f_WT=2"
        
    processed_jobs = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_path = os.path.join(base_dir, "vagas_otimizadas", "processed_jobs.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                processed_jobs = json.load(f)
        except Exception:
            pass
            
    processed_ids = {job.get("id") for job in processed_jobs}
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(4000)
            
            content = await page.content()
            await browser.close()
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"
            return
            
        soup = BeautifulSoup(content, 'lxml')
        
        cards = soup.find_all("div", class_=lambda x: x and "job-search-card" in x)
        if not cards:
            cards = soup.find_all("li", class_=lambda x: x and "jobs-search__results-list" in x)
            if not cards:
                cards = soup.find_all("a", href=lambda h: h and "/jobs/view" in h)
        
        yielded_count = 0
        for card in cards:
            if yielded_count >= 10:
                break
            try:
                if card.name == 'a':
                    href = card.get("href", "")
                    title = card.get_text(strip=True) or "Vaga sem título"
                    clean_url = href.split('?')[0]
                    job_id = clean_url.split('/view/')[-1].split('/')[0] if '/view/' in clean_url else clean_url
                    if job_id not in processed_ids:
                        job_obj = {
                            "id": job_id,
                            "title": title,
                            "company": "LinkedIn Job",
                            "location": location,
                            "url": clean_url
                        }
                        import asyncio
                        await asyncio.sleep(0.3)
                        yield json.dumps(job_obj) + "\n"
                        yielded_count += 1
                    continue
                
                title_el = card.find("h3", class_=lambda x: x and "title" in x) or card.find(class_=lambda x: x and "title" in x)
                company_el = card.find("h4", class_=lambda x: x and "subtitle" in x) or card.find("a", class_=lambda x: x and "subtitle" in x)
                location_el = card.find(class_=lambda x: x and "location" in x)
                link_el = card.find("a", href=lambda h: h and "/jobs/view" in h) or card.find("a", class_=lambda x: x and "link" in x)
                
                if not link_el and card.name == 'a':
                    link_el = card
                    
                if title_el and link_el:
                    title = title_el.get_text(strip=True)
                    company = company_el.get_text(strip=True) if company_el else "Empresa não informada"
                    loc = location_el.get_text(strip=True) if location_el else location
                    href = link_el.get("href", "")
                    clean_url = href.split('?')[0]
                    job_id = clean_url.split('/view/')[-1].split('/')[0] if '/view/' in clean_url else clean_url
                    
                    if job_id not in processed_ids:
                        job_obj = {
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "location": loc,
                            "url": clean_url
                        }
                        import asyncio
                        await asyncio.sleep(0.3)
                        yield json.dumps(job_obj) + "\n"
                        yielded_count += 1
            except Exception as ex:
                continue
                
        async for post_job_json in _internal_search_posts(keywords, processed_ids, p):
            yield post_job_json
