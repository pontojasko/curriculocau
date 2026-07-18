#!/bin/bash

echo "==================================================="
echo "              CURRICULO-CAU - Gruvbox"
echo "       [ Curriculum Analyzer & Upgrader ]"
echo "==================================================="
echo ""

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if python3 is available
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "Erro: Python nao encontrado. Por favor, instale o Python."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[1/3] Criando ambiente virtual (venv)..."
    $PYTHON -m venv venv
fi

echo "[2/3] Ativando ambiente virtual e verificando dependencias..."
source venv/bin/activate
pip install -q -r requirements.txt

echo "[3/3] Iniciando aplicacao..."
python run.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Ocorreu um erro ao iniciar a aplicacao."
    read -p "Pressione Enter para sair..."
fi
