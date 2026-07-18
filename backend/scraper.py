from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os

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
            
        return {
            "title": title,
            "description": clean_text
        }

async def search_linkedin_jobs(keywords: str, location: str = "Brasil", remote_only: bool = False):
    import urllib.parse
    
    if location.strip().lower() == "brasil":
        location = "Brazil"
        
    if remote_only:
        keywords = f"({keywords}) AND (Remoto OR Remote OR \"Home Office\")"
        
    encoded_keywords = urllib.parse.quote(keywords)
    encoded_location = urllib.parse.quote(location)
    url = f"https://www.linkedin.com/jobs/search?keywords={encoded_keywords}&location={encoded_location}"
    if remote_only:
        url += "&f_WT=3"
    
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
            return {"error": str(e)}
            
        soup = BeautifulSoup(content, 'lxml')
        jobs = []
        
        cards = soup.find_all("div", class_=lambda x: x and "job-search-card" in x)
        if not cards:
            cards = soup.find_all("li", class_=lambda x: x and "jobs-search__results-list" in x)
            if not cards:
                cards = soup.find_all("a", href=lambda h: h and "/jobs/view" in h)
        
        for card in cards:
            try:
                if card.name == 'a':
                    href = card.get("href", "")
                    title = card.get_text(strip=True) or "Vaga sem título"
                    clean_url = href.split('?')[0]
                    jobs.append({
                        "id": clean_url.split('/view/')[-1].split('/')[0] if '/view/' in clean_url else clean_url,
                        "title": title,
                        "company": "LinkedIn Job",
                        "location": location,
                        "url": clean_url
                    })
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
                    
                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": loc,
                        "url": clean_url
                    })
            except Exception as ex:
                continue
                
        return {"jobs": jobs[:15]}
