import os
import shutil
import tempfile
import asyncio
import urllib.request
import json
import zipfile
import io

def download_tectonic(dest_dir: str) -> str:
    """Downloads and extracts the Tectonic compiler binary to the destination directory."""
    print("Buscando versão mais recente do Tectonic...")
    url = "https://api.github.com/repos/tectonic-typesetting/tectonic/releases/latest"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
    download_url = None
    for asset in data.get('assets', []):
        name = asset.get('name', '')
        if 'x86_64-pc-windows-msvc.zip' in name:
            download_url = asset.get('browser_download_url')
            break
            
    if not download_url:
        raise Exception("Não foi possível encontrar o binário Tectonic para Windows nos assets do GitHub.")
        
    print(f"Baixando Tectonic de: {download_url}")
    zip_req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(zip_req) as zip_resp:
        zip_data = zip_resp.read()
        
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        for file_info in z.infolist():
            if file_info.filename.endswith('.exe'):
                z.extract(file_info, dest_dir)
                return os.path.join(dest_dir, file_info.filename)
                
    raise Exception("tectonic.exe não encontrado dentro do zip.")

async def compile_latex(latex_code: str, base_dir: str) -> tuple[bool, str, str]:
    """
    Compiles LaTeX code in an isolated temporary directory using pdflatex (if available)
    or Tectonic (automatically downloaded).
    Returns (success: bool, pdf_path_or_empty: str, error_log: str)
    """
    # Create isolated temp directory
    temp_dir = tempfile.mkdtemp(prefix="resume_gen_")
    
    # Copy resume.cls to temp directory
    cls_source = os.path.join(base_dir, "resume.cls")
    cls_dest = os.path.join(temp_dir, "resume.cls")
    if os.path.exists(cls_source):
        shutil.copy2(cls_source, cls_dest)
        
    tex_path = os.path.join(temp_dir, "resume.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_code)
        
    # Determine which compiler to use
    if shutil.which("pdflatex"):
        compiler_cmd = ["pdflatex", "--no-shell-escape", "-interaction=nonstopmode", "resume.tex"]
    else:
        # Fallback to local tectonic
        bin_dir = os.path.join(base_dir, "backend", "bin")
        tectonic_path = os.path.join(bin_dir, "tectonic.exe")
        
        if not os.path.exists(tectonic_path):
            try:
                download_tectonic(bin_dir)
            except Exception as e:
                return False, "", f"Erro ao baixar Tectonic automaticamente: {str(e)}"
                
        compiler_cmd = [tectonic_path, "resume.tex"]

    try:
        import subprocess
        
        def run_compiler_sync(cmd, cwd):
            # Run compiler synchronously in thread
            res = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=35.0
            )
            return res.returncode, res.stdout, res.stderr

        returncode, stdout, stderr = await asyncio.to_thread(
            run_compiler_sync, compiler_cmd, temp_dir
        )

        output_log = stdout.decode('utf-8', errors='ignore') + "\n" + stderr.decode('utf-8', errors='ignore')
        
        pdf_path = os.path.join(temp_dir, "resume.pdf")
        if returncode == 0 and os.path.exists(pdf_path):
            return True, pdf_path, output_log
        else:
            return False, "", output_log
            
    except subprocess.TimeoutExpired:
        return False, "", "O processo de compilação estourou o limite de tempo (timeout de 35s)."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, "", f"Exceção durante a compilação:\n{traceback.format_exc()}"
