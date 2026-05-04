#!/bin/bash
# Quick test for strict metadata isolation

WS_URL="wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

echo "================================================================================"
echo "QUICK ISOLATION TEST"
echo "================================================================================"
echo ""

# Test 1: Project 165 should find Luis
echo "🧪 Test 1: Project 165 → Should find Luis birthplace"
echo '{"action":"sendMessage","data":{"inputText":"¿Dónde nació Luis Fernández?","sessionId":"quick-test","tenant_id":"1001","project_id":"165"}}' | wscat -c "$WS_URL" -x 2>&1 | grep -v "connected" | head -15
echo ""
sleep 3

# Test 2: Project 6636 should NOT find Luis (KEY TEST)
echo "🧪 Test 2: Project 6636 → Should NOT find Luis (different project)"
echo '{"action":"sendMessage","data":{"inputText":"¿Quién es Luis Fernández?","sessionId":"quick-test","tenant_id":"1001","project_id":"6636"}}' | wscat -c "$WS_URL" -x 2>&1 | grep -v "connected" | head -15
echo ""
sleep 3

# Test 3: Task 174 should find achievements
echo "🧪 Test 3: Task 174 → Should find Luis achievements"
echo '{"action":"sendMessage","data":{"inputText":"¿Qué hazañas ha realizado Luis?","sessionId":"quick-test","tenant_id":"1001","project_id":"165","task_id":"174"}}' | wscat -c "$WS_URL" -x 2>&1 | grep -v "connected" | head -15
echo ""
sleep 3

# Test 4: Task 174 should NOT find birthplace (project-level data)
echo "🧪 Test 4: Task 174 → Should NOT find birthplace (project-level data excluded)"
echo '{"action":"sendMessage","data":{"inputText":"¿Dónde nació Luis?","sessionId":"quick-test","tenant_id":"1001","project_id":"165","task_id":"174"}}' | wscat -c "$WS_URL" -x 2>&1 | grep -v "connected" | head -15
echo ""

echo "================================================================================"
echo "✅ TESTS COMPLETE"
echo "================================================================================"
echo ""
echo "Expected results:"
echo "  Test 1: ✅ 'Santa Marta' (project-level doc accessible)"
echo "  Test 2: ❌ 'no tengo información' (cross-project isolation)"
echo "  Test 3: ✅ '40 km descalzo' (task-level doc accessible)"
echo "  Test 4: ❌ 'no tengo información' (project-level excluded from task)"
echo ""
