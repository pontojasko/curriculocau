import json
import os
import re
import shutil
import asyncio
import random
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.pipeline import generation_pipeline
from backend.scraper import scrape_job_url

app = FastAPI()

BATCH_STATE = {
    "status": "idle",
    "jobs": {},
    "logs": ""
}

# Mount frontend static files
app.mount("/_app", StaticFiles(directory="frontend-svelte/build/_app"), name="svelte_assets")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class GenerateRequest(BaseModel):
    job_description: str
    model: str

@app.get("/")
async def read_root():
    return FileResponse("frontend-svelte/build/index.html")

@app.get("/api/models")
async def get_models():
    """Reads models from the local json file and parses their API ID."""
    models_path = os.path.join(BASE_DIR, "nvidia_models.json")
    try:
        with open(models_path, 'r', encoding='utf-8') as f:
            models = json.load(f)
        
        formatted_models = []
        for m in models:
            link = m.get("link", "")
            if "build.nvidia.com/" in link:
                model_id = link.split("build.nvidia.com/")[-1]
                # Replace underscores in version numbers with dots (e.g. llama-3_1 -> llama-3.1, v1_5 -> v1.5)
                model_id = re.sub(r'(\d+)_(\d+)', r'\1.\2', model_id)
                formatted_models.append({
                    "title": m.get("title", model_id),
                    "id": model_id
                })
        return {"models": formatted_models}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/generate")
async def generate_resume(req: GenerateRequest):
    """
    Returns a StreamingResponse (SSE) that yields progress logs and 
    finally the generated PDF path.
    """
    # Sanitize the model ID to replace underscores in version numbers with dots (failsafe for cache)
    sanitized_model = re.sub(r'(\d+)_(\d+)', r'\1.\2', req.model)
    return StreamingResponse(
        generation_pipeline(req.job_description, sanitized_model, BASE_DIR),
        media_type="text/event-stream"
    )

class ScrapeRequest(BaseModel):
    url: str

@app.post("/api/scrape")
async def scrape_job(req: ScrapeRequest):
    """Scrapes job title and description from a URL using Obscura CDP."""
    result = await scrape_job_url(req.url)
    return result

class SearchJobsRequest(BaseModel):
    keywords: str
    negative_keywords: str = ""
    location: str = "Brasil"
    remote_only: bool = False

@app.post("/api/search-jobs")
async def search_jobs(req: SearchJobsRequest):
    from backend.scraper import search_linkedin_jobs
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        search_linkedin_jobs(req.keywords, req.negative_keywords, req.location, req.remote_only),
        media_type="application/x-ndjson"
    )

class BatchProcessRequest(BaseModel):
    jobs: list
    model: str

async def process_batch_jobs_task(jobs_to_process: list, model: str):
    global BATCH_STATE
    BATCH_STATE["status"] = "running"
    BATCH_STATE["logs"] = "Iniciando processamento em lote...\n"
    
    for job in jobs_to_process:
        job_id = job["id"]
        BATCH_STATE["jobs"][job_id] = {
            "title": job["title"],
            "company": job["company"],
            "url": job["url"],
            "status": "pending",
            "pdf_path": "",
            "error": ""
        }
    
    for job in jobs_to_process:
        job_id = job["id"]
        # Check if the state was cleared or reset concurrently
        if BATCH_STATE.get("status") != "running" or "jobs" not in BATCH_STATE or job_id not in BATCH_STATE["jobs"]:
            break
            
        BATCH_STATE["jobs"][job_id]["status"] = "scraping"
        BATCH_STATE["logs"] += f"\n>>> Processando vaga: {job['title']} na {job['company']}\n"
        BATCH_STATE["logs"] += "[SCRAPING] Extraindo informações via Obscura CDP...\n"
        
        try:
            url = job["url"]
            scrape_result = await scrape_job_url(url)
            
            # Check after async yield
            if BATCH_STATE.get("status") != "running" or "jobs" not in BATCH_STATE or job_id not in BATCH_STATE["jobs"]:
                break
                
            if "error" in scrape_result:
                BATCH_STATE["jobs"][job_id]["status"] = "failed"
                BATCH_STATE["jobs"][job_id]["error"] = f"Erro ao extrair vaga: {scrape_result['error']}"
                BATCH_STATE["logs"] += f"[ERRO] {scrape_result['error']}\n"
                continue
                
            job_text = f"{scrape_result.get('title', '')}\n\n{scrape_result.get('description', '')}"
            BATCH_STATE["jobs"][job_id]["status"] = "generating"
            BATCH_STATE["logs"] += "[EXTRAÇÃO] Sucesso! Iniciando geração do PDF otimizado...\n"
            
            pdf_path = None
            error_msg = None
            
            async for sse_event in generation_pipeline(job_text, model, BASE_DIR):
                if sse_event.startswith("data: "):
                    try:
                        event_data = json.loads(sse_event[6:].strip())
                        if event_data.get("type") == "stream":
                            # Check state still valid before appending logs
                            if BATCH_STATE.get("status") == "running":
                                BATCH_STATE["logs"] += event_data.get("message", "")
                        else:
                            msg_type = event_data.get("type", "info").upper()
                            if BATCH_STATE.get("status") == "running":
                                BATCH_STATE["logs"] += f"\n[{msg_type}] {event_data.get('message', '')}\n"
                            
                        if event_data.get("type") == "success":
                            pdf_path = event_data.get("message")
                        elif event_data.get("type") == "error":
                            error_msg = event_data.get("message")
                    except:
                        pass
                        
            # Check after pipeline yield
            if BATCH_STATE.get("status") != "running" or "jobs" not in BATCH_STATE or job_id not in BATCH_STATE["jobs"]:
                break
                
            if pdf_path and os.path.exists(pdf_path):
                target_dir = os.path.join(BASE_DIR, "vagas_otimizadas")
                os.makedirs(target_dir, exist_ok=True)
                
                clean_company = re.sub(r'[^a-zA-Z0-9]', '_', job["company"])
                clean_title = re.sub(r'[^a-zA-Z0-9]', '_', job["title"])
                filename = f"{clean_company}_{clean_title}.pdf"
                dest_path = os.path.join(target_dir, filename)
                
                shutil.copy2(pdf_path, dest_path)
                
                BATCH_STATE["jobs"][job_id]["status"] = "completed"
                BATCH_STATE["jobs"][job_id]["pdf_path"] = dest_path
            else:
                BATCH_STATE["jobs"][job_id]["status"] = "failed"
                BATCH_STATE["jobs"][job_id]["error"] = error_msg or "Falha desconhecida na geração"
                BATCH_STATE["logs"] += f"[ERRO GERANDO PDF] {BATCH_STATE['jobs'][job_id]['error']}\n"
                
        except Exception as e:
            if "jobs" in BATCH_STATE and job_id in BATCH_STATE["jobs"]:
                BATCH_STATE["jobs"][job_id]["status"] = "failed"
                BATCH_STATE["jobs"][job_id]["error"] = str(e)
            if "logs" in BATCH_STATE:
                BATCH_STATE["logs"] += f"[FATAL ERRO] {str(e)}\n"
            
        # Random sleep between 6 and 12 seconds to mimic human and avoid rate limits
        if job != jobs_to_process[-1]:
            sleep_time = random.uniform(6, 12)
            if BATCH_STATE.get("status") == "running":
                BATCH_STATE["logs"] += f"\n[SISTEMA] Aguardando {sleep_time:.1f}s antes da próxima vaga para evitar bloqueios...\n"
            await asyncio.sleep(sleep_time)
            
    if BATCH_STATE.get("status") == "running":
        BATCH_STATE["status"] = "completed"
        BATCH_STATE["logs"] += "\n[SISTEMA] Processamento em lote finalizado!\n"

@app.post("/api/batch-process")
async def batch_process(req: BatchProcessRequest, background_tasks: BackgroundTasks):
    global BATCH_STATE
    if BATCH_STATE["status"] == "running":
        return {"error": "A batch process is already running"}
        
    sanitized_model = re.sub(r'(\d+)_(\d+)', r'\1.\2', req.model)
    background_tasks.add_task(process_batch_jobs_task, req.jobs, sanitized_model)
    return {"status": "started"}

@app.get("/api/batch-status")
async def get_batch_status():
    global BATCH_STATE
    return BATCH_STATE

import tempfile

@app.get("/api/download")
async def download_pdf(path: str):
    """Downloads the generated PDF."""
    if not os.path.exists(path) or not path.endswith('.pdf'):
        return {"error": "File not found or invalid"}
        
    # SECURITY: Prevent Path Traversal by ensuring the file is inside the system's temp directory
    abs_path = os.path.abspath(path)
    temp_dir = os.path.abspath(tempfile.gettempdir())
    vagas_dir = os.path.abspath(os.path.join(BASE_DIR, "vagas_otimizadas"))
    
    if not (abs_path.startswith(temp_dir) or abs_path.startswith(vagas_dir)):
        return {"error": "Access denied. Invalid file path."}
        
    return FileResponse(path, filename="resume_optimized.pdf", media_type="application/pdf")

@app.delete("/api/clear-cache")
async def clear_cache():
    global BATCH_STATE
    if BATCH_STATE.get("status") == "running":
        return {"error": "Cannot clear cache while a batch process is running"}
        
    cache_path = os.path.join(BASE_DIR, "vagas_otimizadas", "processed_jobs.json")
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception as e:
            return {"error": f"Failed to delete cache file: {str(e)}"}
            
    BATCH_STATE = {
        "status": "idle",
        "jobs": {},
        "logs": ""
    }
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
