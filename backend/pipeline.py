import json
import asyncio
import re
from backend.ai_service import generate_optimized_resume, extract_latex, analyze_job_description
from backend.latex_compiler import compile_latex

def get_pdf_page_count(pdf_path: str) -> int:
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        print(f"Error reading PDF page count: {e}")
        return 1

def extract_latex_errors(log_text: str) -> str:
    """Extracts the main LaTeX error messages from a compilation log."""
    errors = []
    for line in log_text.split('\n'):
        line_strip = line.strip()
        if line_strip.startswith('!') or line_strip.startswith('error:') or 'LaTeX Error:' in line_strip:
            errors.append(line_strip)
    if not errors:
        # Fallback to showing last 8 lines of log
        non_empty = [l.strip() for l in log_text.split('\n') if l.strip()]
        return "\n".join(non_empty[-8:])
    return "\n".join(errors[:5])

async def generation_pipeline(job_description: str, model: str, base_dir: str, max_retries: int = 3):
    """
    Orchestrates the generation and auto-correction loop.
    Yields JSON strings to be sent via SSE.
    """
    
    def format_sse(event_type: str, data: str):
        return f"data: {json.dumps({'type': event_type, 'message': data})}\n\n"
        
    yield format_sse("info", f"Lendo currículo original (PTBR.tex)...")
    
    tex_file_path = f"{base_dir}/PTBR.tex"
    try:
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            original_latex = f.read()
    except Exception as e:
        yield format_sse("error", f"Falha ao ler PTBR.tex: {str(e)}")
        return

    # 1. Run Job Analysis (Stage 1) with streaming
    yield format_sse("info", "Iniciando análise inteligente da vaga e matching (Etapa 1)...")
    analysis_json = None
    try:
        full_analysis_chunks = []
        yield format_sse("analysis_stream_start", "")
        async for chunk in analyze_job_description(model, job_description, original_latex):
            full_analysis_chunks.append(chunk)
            yield format_sse("analysis_stream", chunk)
            
        full_analysis = "".join(full_analysis_chunks).strip()
        if full_analysis.startswith("```"):
            full_analysis = re.sub(r'^```(?:json)?\n', '', full_analysis)
            full_analysis = re.sub(r'\n```$', '', full_analysis)
        analysis_json = full_analysis.strip()
        
        yield format_sse("analysis", analysis_json)
        yield format_sse("info", "Análise de match concluída com sucesso!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield format_sse("warning", f"Não foi possível concluir a análise diagnóstica: {str(e)}. Prosseguindo diretamente...")

    error_log = None
    
    for attempt in range(1, max_retries + 1):
        if attempt == 1:
            yield format_sse("info", f"Iniciando tentativa {attempt}/{max_retries}: Solicitando IA ({model}) para reescrever o currículo...")
        else:
            yield format_sse("info", f"Iniciando tentativa de auto-correção {attempt}/{max_retries}...")
            
        # 2. Generate / Correct with streaming (Stage 2)
        try:
            full_response_chunks = []
            yield format_sse("stream_start", "")
            
            async for chunk in generate_optimized_resume(model, job_description, original_latex, analysis_json, error_log):
                full_response_chunks.append(chunk)
                yield format_sse("stream", chunk)
                
            full_response = "".join(full_response_chunks)
            new_latex = extract_latex(full_response)
            yield format_sse("info", "Código LaTeX gerado com sucesso! Iniciando compilação...")
        except Exception as e:
            yield format_sse("warning", f"Falha na IA na tentativa {attempt}/{max_retries}: {str(e)}")
            if attempt < max_retries:
                yield format_sse("info", "Aguardando 2 segundos antes de tentar novamente...")
                await asyncio.sleep(2)
                continue
            else:
                yield format_sse("error", f"Falha persistente na IA após {max_retries} tentativas: {str(e)}")
                return
            
        # 2. Compile
        yield format_sse("info", "Compilando PDF...")
        success, pdf_path, log = await compile_latex(new_latex, base_dir)
        
        if success:
            page_count = get_pdf_page_count(pdf_path)
            if page_count > 1:
                error_log = f"LAYOUT_WARNING: {page_count}"
                yield format_sse("warning", f"Tentativa {attempt} compilou com sucesso, mas gerou {page_count} páginas (estourou o limite de 1 página).\nSolicitando compactação de layout para a IA...")
                continue
            yield format_sse("success", pdf_path)
            return
        else:
            extracted_errors = extract_latex_errors(log)
            error_log = log[-2000:] # Send last 2000 chars to avoid token limits
            yield format_sse("warning", f"Tentativa {attempt} falhou na compilação.\n[ERROS DE COMPILAÇÃO]:\n{extracted_errors}\n\nSolicitando correção para a IA...")
            
    yield format_sse("error", f"Falha ao compilar ou ajustar tamanho após {max_retries} tentativas. Abortando.")
