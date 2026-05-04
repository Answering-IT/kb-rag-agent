#!/bin/bash
# Test strict metadata isolation with partition_key

WS_URL="wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

echo "================================================================================"
echo "STRICT METADATA ISOLATION TEST (with partition_key)"
echo "================================================================================"
echo ""

# Function to test with wscat
test_query() {
    local test_name="$1"
    local tenant_id="$2"
    local project_id="$3"
    local task_id="$4"
    local question="$5"
    local expected="$6"

    echo "--------------------------------------------------------------------------------"
    echo "🧪 $test_name"
    echo "--------------------------------------------------------------------------------"
    echo "   Metadata: tenant=$tenant_id, project=$project_id, task=$task_id"
    echo "   Question: $question"
    echo "   Expected: $expected"
    echo ""

    # Build JSON payload
    if [ -z "$task_id" ]; then
        if [ -z "$project_id" ]; then
            payload="{\"action\":\"sendMessage\",\"data\":{\"inputText\":\"$question\",\"sessionId\":\"test-strict\",\"tenant_id\":\"$tenant_id\"}}"
        else
            payload="{\"action\":\"sendMessage\",\"data\":{\"inputText\":\"$question\",\"sessionId\":\"test-strict\",\"tenant_id\":\"$tenant_id\",\"project_id\":\"$project_id\"}}"
        fi
    else
        payload="{\"action\":\"sendMessage\",\"data\":{\"inputText\":\"$question\",\"sessionId\":\"test-strict\",\"tenant_id\":\"$tenant_id\",\"project_id\":\"$project_id\",\"task_id\":\"$task_id\"}}"
    fi

    echo "   📤 Sending..."
    echo "$payload" | wscat -c "$WS_URL" -x | grep -v "connected" | head -20
    echo ""
    sleep 2
}

# Test 1: Tenant only (should access all tenant docs)
test_query \
    "Test 1a: Tenant only - Luis" \
    "1001" \
    "" \
    "" \
    "¿Quién es Luis Fernández?" \
    "✅ Should find Luis (all tenant docs accessible)"

test_query \
    "Test 1b: Tenant only - Juan Daniel" \
    "1001" \
    "" \
    "" \
    "¿Quién es Juan Daniel Pérez?" \
    "✅ Should find Juan Daniel (all tenant docs accessible)"

# Test 2: Project 165 (Luis's project)
test_query \
    "Test 2a: Project 165 - Luis basic info" \
    "1001" \
    "165" \
    "" \
    "¿Dónde nació Luis Fernández?" \
    "✅ Should find Luis birthplace (project-level doc)"

test_query \
    "Test 2b: Project 165 - Juan Daniel (wrong project)" \
    "1001" \
    "165" \
    "" \
    "¿Quién es Juan Daniel Pérez?" \
    "❌ Should NOT find Juan Daniel (he's in project 6636)"

test_query \
    "Test 2c: Project 165 - Luis achievements (task data, NO task_id)" \
    "1001" \
    "165" \
    "" \
    "¿Qué hazañas ha realizado Luis?" \
    "❌ Should NOT find achievements (task_id required for task-level docs)"

# Test 3: Project 6636 (Juan Daniel's project)
test_query \
    "Test 3a: Project 6636 - Juan Daniel" \
    "1001" \
    "6636" \
    "" \
    "¿Quién es Juan Daniel Pérez?" \
    "✅ Should find Juan Daniel (he's in project 6636)"

test_query \
    "Test 3b: Project 6636 - Luis (wrong project)" \
    "1001" \
    "6636" \
    "" \
    "¿Quién es Luis Fernández?" \
    "❌ Should NOT find Luis (he's in project 165)"

# Test 4: Task 174 (Luis's achievements)
test_query \
    "Test 4a: Task 174 - Luis achievements" \
    "1001" \
    "165" \
    "174" \
    "¿Qué hazañas ha realizado Luis?" \
    "✅ Should find achievements (task-level doc with task_id=174)"

test_query \
    "Test 4b: Task 174 - Luis birthplace (project-level)" \
    "1001" \
    "165" \
    "174" \
    "¿Dónde nació Luis?" \
    "❌ Should NOT find birthplace (project-level doc, task_id=174 excludes it)"

# Test 5: Wrong task
test_query \
    "Test 5a: Task 999 (wrong) - Luis achievements" \
    "1001" \
    "165" \
    "999" \
    "¿Qué hazañas ha realizado Luis?" \
    "❌ Should NOT find achievements (task 174 doc not accessible from task 999)"

echo "================================================================================"
echo "✅ TEST SUITE COMPLETE"
echo "================================================================================"
echo ""
echo "Expected behavior summary:"
echo "  ✅ tenant_id only → All tenant docs"
echo "  ✅ tenant_id + project_id → ONLY project-level docs (excludes tasks)"
echo "  ✅ tenant_id + project_id + task_id → ONLY task-level docs (excludes project)"
echo ""
