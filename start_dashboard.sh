#!/bin/bash
# Executável de inicialização do Dashboard Unificado de Parceiros
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  DASHBOARD UNIFICADO DE PARCEIROS LÉO MADEIRAS"
echo "=========================================================="
echo "Sincronizando planilhas do OneDrive e iniciando servidor..."
echo ""

PYTHONUNBUFFERED=1 python3 server.py 3000 &
SERVER_PID=$!

sleep 2
echo "Abrindo o Dashboard no seu navegador..."
open "http://localhost:3000"

wait $SERVER_PID
