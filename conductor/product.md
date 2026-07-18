# AI Resume Optimizer (curriculo-cau)

## Vision
A tool that leverages NVIDIA AI (DeepSeek v4 Pro, Llama 3.3, etc.) to adapt and optimize LaTeX resumes based on job descriptions, maximizing the chances of passing ATS systems and catching recruiters' attention.

## Problem Statement & Solution Approach
Job seekers struggle to tailor their resumes for every single application. The solution is an AI-powered local compiler that analyzes a job description (via text or URL scraping), matches it against the candidate's LaTeX resume, and generates a tailored 1-page PDF using high-signal prioritization without lying or breaking formatting.

## Target Audience
Job seekers and professionals who use LaTeX for their resumes.

## Features
- Upload/paste a job description or URL (Scraping via Obscura).
- Select from multiple NVIDIA AI models (ranked by intelligence).
- Real-time AI thinking/progress logs (SSE).
- Robust AI rewriting of the `.tex` file without breaking formatting.
- Auto-correction loop for LaTeX compilation errors.
- One-click PDF download of the optimized resume.
- Diagnostic Match Score and Gaps analysis.

## Success Metrics (KPIs)
- **Compilation Success Rate:** > 95% sem quebrar o layout.
- **Match Score Average:** Currículos gerados devem atingir > 80% de aderência na avaliação cruzada.
- **Performance:** Retorno da IA e compilação do PDF em < 45 segundos.

## Roadmap
1. Base implementation (Backend FastAPI + SvelteKit Frontend) - **DONE**
2. Security and resilience fixes (Path Traversal, SSE chunking) - **IN PROGRESS**
3. Testing and auto-correction refinement.
