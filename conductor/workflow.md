# Workflow Guidelines

## Security & Architecture
- API Keys must never be committed (`.env` in `.gitignore`).
- Asynchronous patterns should be used in FastAPI (especially for subprocesses to avoid event loop blocking).
- LaTeX compilation must occur in isolated temporary directories (`tempfile.mkdtemp()`) and must use `--no-shell-escape` for security.
- **File System Security:** Endpoint de download deve restringir acesso estritamente ao diretório temporário do sistema para prevenir ataques de Path Traversal (LFI).
- Resumes are generated using an auto-correction loop: Generate -> Compile -> (if fail) Feed error to AI -> Retry.

## Development Methodology
- **Context-Driven Development (CDD):** Sempre consulte a pasta `conductor/` antes de codar e atualize-a ao concluir features.
- Testes locais rigorosos antes do commit.

## Git Workflow
- Conventional Commits obrigatório (ex: `feat: add tectonic fallback`, `fix: path traversal vulnerability`).
