# Python Code Styleguide (Backend)

- **Framework:** FastAPI
- **Typing:** Type hints são fortemente recomendados para injetar robustez (ex: `def func(req: Request) -> Response:`).
- **Format:** PEP8 compliance. Usar nomes descritivos com `snake_case`.
- **Async:** Funções I/O bound ou chamadas de sub-processos pesadas (ex: `pdflatex`) DEVEM usar `asyncio` e `to_thread` para não bloquear o Event Loop principal.
- **Security:** Nenhuma rota que aceite caminhos de arquivo do usuário deve usar esse caminho cegamente. Use `os.path.abspath` e valide com `startswith` contra diretórios seguros conhecidos.
