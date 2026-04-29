#!/bin/bash

# Script para iniciar la demo del widget
# Requiere dos terminales

echo "=================================================="
echo "  Chat Widget Integration - Demo Starter"
echo "=================================================="
echo ""

# Verificar que estamos en el directorio correcto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📋 Checklist Pre-inicio:"
echo ""
echo "  ✓ Script ubicado en: $SCRIPT_DIR"
echo "  ✓ Next.js frontend en: $SCRIPT_DIR/fe"
echo "  ✓ Angular app en: /Users/qohatpretel/Answering/REP_FE_COLPENSIONES"
echo ""

# Función para verificar si un puerto está en uso
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Puerto $1 ya está en uso"
        return 1
    else
        echo "✅ Puerto $1 disponible"
        return 0
    fi
}

echo "🔍 Verificando puertos..."
check_port 3000
check_port 4200
echo ""

echo "=================================================="
echo "  Instrucciones de Inicio"
echo "=================================================="
echo ""
echo "Necesitas abrir 2 TERMINALES:"
echo ""
echo "📱 TERMINAL 1 - Next.js Frontend:"
echo "   cd $SCRIPT_DIR/fe"
echo "   npm run dev"
echo ""
echo "📱 TERMINAL 2 - Angular App:"
echo "   cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES"
echo "   npm run start-dev"
echo ""
echo "=================================================="
echo ""

# Preguntar al usuario qué quiere hacer
echo "¿Qué quieres hacer?"
echo "  1) Iniciar Next.js (Terminal actual)"
echo "  2) Iniciar Angular (Terminal actual)"
echo "  3) Ver instrucciones completas"
echo "  4) Salir"
echo ""
read -p "Opción (1-4): " option

case $option in
    1)
        echo ""
        echo "🚀 Iniciando Next.js en puerto 3000..."
        echo ""
        cd "$SCRIPT_DIR/fe"
        npm run dev
        ;;
    2)
        echo ""
        echo "🚀 Iniciando Angular con start-dev..."
        echo ""
        cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES
        npm run start-dev
        ;;
    3)
        echo ""
        cat "$SCRIPT_DIR/QUICK-START-WIDGET.md"
        ;;
    4)
        echo "👋 Adiós!"
        exit 0
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac
