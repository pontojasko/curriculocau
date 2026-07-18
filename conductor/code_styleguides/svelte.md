# Svelte Code Styleguide (Frontend)

- **Framework:** SvelteKit + Tailwind CSS (v4)
- **State Management:** Svelte 5 Runes (`$state`, `$effect`, `$derived`). Não usar stores antigas.
- **Styling:** Usar classes utilitárias do Tailwind e variáveis CSS injetadas do tema Gruvbox (ex: `bg-gb-bg`, `text-gb-yellow`).
- **Data Fetching:** Preferir `fetch` nativo em funções async; tratamento rigoroso de exceções (`try/catch/finally`).
- **Streaming (SSE):** O consumo de eventos do servidor (SSE) via `ReadableStream` deve usar bufferização adequada para não quebrar JSONs partidos em diferentes pacotes de rede. Não fazer `JSON.parse` direto no chunk recebido.
