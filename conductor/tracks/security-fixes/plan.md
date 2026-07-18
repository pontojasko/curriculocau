# Security Fixes Plan

- [x] Delete `frontend/` directory.
- [x] Update `main.py` -> `download_pdf()` to validate path against system `temp_dir`.
- [x] Update `+page.svelte` -> `runAnalysis()` stream processing to use a string buffer and split properly by `\n`.
