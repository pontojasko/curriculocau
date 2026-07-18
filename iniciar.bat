@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  Script: iniciar.bat
REM  Purpose: Inicia a aplicacao Curriculo-CAU e suas dependencias
REM ============================================================

title Curriculo-CAU (Gruvbox)
cd /d "%~dp0"

call :main %*
set _EXIT_CODE=%ERRORLEVEL%
call :cleanup
echo.
if %_EXIT_CODE% neq 0 (
    echo [FATAL] A execucao falhou com codigo %_EXIT_CODE%.
    pause
) else (
    echo [INFO] Sessao finalizada com sucesso.
)
exit /b %_EXIT_CODE%

:main
    echo ============================================================
    echo                   CURRICULO-CAU
    echo        [ Curriculum Analyzer ^& Upgrader ]
    echo ============================================================
    echo.

    REM Verifica se o Python esta instalado
    where python >NUL 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Python nao encontrado no PATH. Instale o Python para continuar. 1>&2
        exit /b 1
    )

    REM Passo 1: Ambiente Virtual
    echo [1/4] Verificando ambiente virtual...
    if not exist "venv" (
        echo       Criando ambiente virtual venv...
        python -m venv venv
        if !ERRORLEVEL! neq 0 (
            echo ERROR: Falha ao criar venv. 1^>^&2
            exit /b 1
        )
    )

    REM Passo 2: Dependencias
    echo [2/4] Ativando ambiente e verificando dependencias...
    call venv\Scripts\activate.bat || (echo ERROR: Falha ao ativar venv. 1>&2 & exit /b 1)
    python -m pip install -q -r requirements.txt || (echo ERROR: Falha ao instalar dependencias. 1>&2 & exit /b 1)

    REM Passo 3: Obscura
    echo [3/4] Baixando/Verificando Obscura headless browser...
    python backend\setup_obscura.py || (echo ERROR: Falha na configuracao do Obscura. 1>&2 & exit /b 1)

    REM Passo 4: Iniciando Servicos
    echo [4/4] Iniciando Obscura e a aplicacao web...
    
    REM Matar instancias antigas do obscura se existirem
    taskkill /F /IM obscura.exe >NUL 2>&1
    
    start /B "" backend\bin\obscura.exe serve --stealth -p 9223 >NUL 2>&1
    
    echo.
    echo ============================================================
    echo   Servidor iniciado!
    echo   Acesse http://127.0.0.1:8000 no seu navegador.
    echo   (Para encerrar, feche esta janela ou pressione Ctrl+C)
    echo ============================================================
    echo.
    
    python run.py || (echo ERROR: A aplicacao encerrou de forma inesperada. 1>&2 & exit /b 1)

    exit /b 0

:cleanup
    echo [INFO] Encerrando servicos em background (Obscura)...
    taskkill /F /IM obscura.exe >NUL 2>&1
    exit /b 0
