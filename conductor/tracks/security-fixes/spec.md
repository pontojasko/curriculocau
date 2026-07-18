# Security & Resilience Spec

## Requirements
1. **Path Traversal Fix:** O endpoint `/api/download` do FastAPI não deve aceitar caminhos absolutos arbitrários do cliente, prevenindo LFI (Local File Inclusion).
2. **SSE Streaming Resilience:** O consumo do stream no SvelteKit deve usar um buffer para evitar quebra no parser JSON se os pacotes de rede separarem a string ao meio.
3. **Remoção de Código Morto:** Deletar a pasta `frontend/` legada (Vanilla JS) já que o projeto migrou para SvelteKit (Gruvbox).
