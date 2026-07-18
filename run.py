import os
import sys
import subprocess
import time
import webbrowser

def main():
    url = "http://127.0.0.1:8000"
    
    # Configure PYTHONPATH to include current directory
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    print("\nIniciando o servidor FastAPI...")
    
    try:
        # Start uvicorn as a subprocess pointing to backend.main
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "backend.main:app", 
            "--host", "127.0.0.1", 
            "--port", "8000",
            "--no-access-log"
        ]
        process = subprocess.Popen(cmd, env=env)
        
        # Wait a brief moment for the port to bind
        time.sleep(1.5)
        
        # Open browser automatically
        print(f"Abrindo navegador em: {url}")
        webbrowser.open(url)
        
        # Wait for the subprocess to finish
        process.wait()
        
    except KeyboardInterrupt:
        print("\n[Desligando] Encerrando o servidor de forma limpa...")
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
    except Exception as e:
        print(f"Ocorreu um erro ao iniciar a aplicacao: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
