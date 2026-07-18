# Tech Stack

## Backend
- Python 3
- FastAPI (Web Framework)
- Uvicorn (ASGI Server)
- OpenAI Python SDK (to communicate with NVIDIA NIM API)
- python-dotenv (Env variables)

## Compilation
- `pdflatex` (local MiKTeX / TeX Live) invoked via Python `asyncio.create_subprocess_exec`.
- `tectonic` fallback (automatically downloaded binary if pdflatex is not found).

## Frontend
- SvelteKit
- Tailwind CSS
- Gruvbox Theme (Dark mode, monospaced fonts, retro terminal aesthetic)

## API Integrations
- NVIDIA NIM API (base_url: `https://integrate.api.nvidia.com/v1`)
- Obscura CDP (para web scraping de vagas)
