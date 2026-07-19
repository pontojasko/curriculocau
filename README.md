<div align="center">
  <img src="assets/title.png" alt="CurriculoCAU" width="640"/>
  <br/>
  <b>local CDP automation engine for LaTeX resume optimization</b>
  <br/><br/>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/pontojasko/curriculocau?style=flat-square&labelColor=282828&color=d79921" alt="License"/></a>
  <a href="https://github.com/pontojasko/curriculocau/stargazers"><img src="https://img.shields.io/github/stars/pontojasko/curriculocau?style=flat-square&labelColor=282828&color=d79921" alt="Stars"/></a>
  <a href="https://github.com/pontojasko/curriculocau/issues"><img src="https://img.shields.io/github/issues/pontojasko/curriculocau?style=flat-square&labelColor=282828&color=d79921" alt="Issues"/></a>
  <br/><br/>
  <img src="assets/demo.gif" alt="Curriculo-CAU running in browser" width="720" />
  <br/>
  <em>Demo</em>
</div>

---

```
[ engine ]     stealth job scraping via headless CDP
[ pipeline ]   batch search → AI tailoring → LaTeX compile
[ output ]     targeted, high-match PDF resumes
```

[`prerequisites`](#prerequisites) • [`installation`](#installation) • [`usage`](#usage)

---

## Features

- **Stealth Job Scraping:** Uses Obscura headless browser via CDP (Chrome DevTools Protocol) to scrape job listings (e.g., LinkedIn) while bypassing anti-bot detection without relying on heavy Chromium installations.
- **Batch Processing Mode:**
  - Search multiple jobs at once using keywords and locations.
  - **YouTube/SoundCloud-style Tagging:** Visual tag elements for both Keywords and Negative Keywords (Banidas) with easy click-to-remove capability.
  - **Dynamic Suggestions:** Curated tech & corporate keyword lists with inline chips and a reload (`⟳`) trigger to rotate suggestions on-the-fly.
  - **Real-Time Streaming (NDJSON):** Results populate the Job Queue progressively as they are scraped by the robot, with an artificial delay for visual feedback, and all incoming jobs are auto-selected by default.
  - **Cache Management:** Built-in clear cache capability (`DELETE /api/clear-cache`) to purge previously processed job IDs and start clean batch runs.
  - Built-in **Boolean Search** automatically injected for Remote jobs (`AND (Remoto OR Remote OR "Home Office")`) and localized `Brasil` -> `Brazil` mapping.
  - Processes multiple selected jobs asynchronously with randomized delays (6-12s) to prevent rate limits and IP bans.
  - **Smart Job Type Detection:** Automatically categorizes jobs into "Easy Apply" (Candidatura Simplificada), "External", and "InHire". Skips unsupported external applications to save resources while queueing supported platforms for processing.
  - **Thread-Safe State Management:** Robust concurrency safeguards when modifying the global `BATCH_STATE` to prevent race conditions during execution and cache clearing.
- **AI-Powered Tailoring:** Integrates with OpenAI-compatible APIs (like NVIDIA NIM) to restructure your resume context into a targeted, high-match application. Enforces strict zero-leak policies to guarantee target company names are never cited in the generated curriculum.
- **LaTeX Compilation:** Generates high-quality PDF resumes seamlessly in the background. The setup script now fully automates the downloading of the `tectonic` binary engine natively—no external installations required.
- **Gruvbox UI:** A premium, retro-terminal Svelte frontend featuring real-time diagnostic consoles, aesthetic physical-style toggle switches, hyperlinked jobs in the pipeline orchestrator, and strict design guidelines.

## Architecture

The project is structured into two main components:

- **Backend (`/backend`)**: Built with Python and FastAPI. Orchestrates the pipeline, manages background tasks for batch processing, and interfaces with the LLM and the Obscura CDP scraper.
- **Frontend (`/frontend-svelte`)**: Built with SvelteKit. Pre-compiled and statically served by FastAPI. Features a reactive UI for both Single Job and Batch Job modes.

## Prerequisites

- **Python 3.10+**
- **Node.js** (Only required if you plan to modify and rebuild the Svelte frontend)
- **Tectonic** (LaTeX engine) - must be available in your system for PDF compilation.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd aicurriculo
   ```
2. **Environment Configuration:**
   Create a `.env` file in the root directory with your API credentials (e.g., NVIDIA NIM or OpenAI keys).

## Usage

The system is designed to be zero-friction.

### Windows

Double-click `iniciar.bat` or run it via terminal:

```bash
iniciar.bat
```

The script will automatically:

- Create a Python virtual environment (`venv`).
- Install backend dependencies from `requirements.txt`.
- Download and set up the Obscura headless browser in stealth mode.
- Start the FastAPI backend and serve the application on `http://127.0.0.1:8000`.

### Linux/macOS

Run the shell script equivalent:

```bash
./iniciar.sh
```

## Development

If you wish to modify the Gruvbox Svelte frontend:

1. Navigate to the frontend directory:
   ```bash
   cd frontend-svelte
   ```
2. Install Node dependencies and start the dev server:
   ```bash
   npm install
   npm run dev
   ```
3. To package your UI changes for FastAPI to serve:
   ```bash
   npm run build
   ```

## License

GNU AFFERO GENERAL PUBLIC LICENSE

## Acknowledgments

- Frontend designed adhering to strict aesthetic and opinionated guidelines (Gruvbox).
- Built with FastAPI, SvelteKit, and Obscura.
