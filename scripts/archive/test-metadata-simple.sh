#!/bin/bash
# Test WebSocket with metadata filtering

WS_URL="wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

echo "=== Test 1: Sin metadata (acceso completo) ==="
wscat -c "$WS_URL" -x '{"action":"sendMessage","data":{"inputText":"¿Qué documentos hay disponibles?","sessionId":"test-no-metadata"}}'

echo -e "\n=== Test 2: Con metadata (tenant=colpensiones) ==="
wscat -c "$WS_URL" -H "x-tenant-id: colpensiones" -x '{"action":"sendMessage","data":{"inputText":"¿Qué documentos hay disponibles?","sessionId":"test-with-metadata","metadata":{"tenant":"colpensiones"}}}'

echo -e "\n=== Test 3: Conversación con contexto ==="
wscat -c "$WS_URL" -x '{"action":"sendMessage","data":{"inputText":"Me llamo Juan","sessionId":"test-context-1"}}'
sleep 2
wscat -c "$WS_URL" -x '{"action":"sendMessage","data":{"inputText":"¿Cómo me llamo?","sessionId":"test-context-1"}}'
