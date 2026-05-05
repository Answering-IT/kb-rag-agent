#!/bin/bash
# Interactive chat with ProcessApp Agent (local)
# Allows testing conversations with metadata filtering

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PORT=8080
BASE_URL="http://localhost:$PORT"
SESSION_ID="chat-local-$(date +%s)"

# Check if agent is running
if ! curl -s $BASE_URL/health &>/dev/null; then
    echo -e "${RED}❌ Error: Agent is not running${NC}"
    echo "Start it with: ./run_local.sh"
    exit 1
fi

echo -e "${GREEN}💬 Interactive Chat with ProcessApp Agent${NC}"
echo "==========================================="
echo ""
echo "Session ID: $SESSION_ID"
echo ""

# Ask for filtering options
echo -e "${YELLOW}Select filtering mode:${NC}"
echo "  1) No filtering (all documents)"
echo "  2) Tenant only (e.g., colpensiones)"
echo "  3) Tenant + Project (e.g., colpensiones/decreto_1833)"
echo "  4) Tenant + Project + Task (e.g., colpensiones/decreto_1833/analisis_legal)"
echo ""
read -p "Enter option (1-4): " FILTER_OPTION

HEADERS=()
case $FILTER_OPTION in
    1)
        echo -e "${CYAN}Mode: No filtering${NC}"
        ;;
    2)
        read -p "Enter tenant ID: " TENANT_ID
        echo -e "${CYAN}Mode: Tenant filtering (${TENANT_ID})${NC}"
        HEADERS+=("-H" "x-tenant-id: $TENANT_ID")
        ;;
    3)
        read -p "Enter tenant ID: " TENANT_ID
        read -p "Enter project ID: " PROJECT_ID
        echo -e "${CYAN}Mode: Tenant + Project (${TENANT_ID}/${PROJECT_ID})${NC}"
        HEADERS+=("-H" "x-tenant-id: $TENANT_ID" "-H" "x-project-id: $PROJECT_ID")
        ;;
    4)
        read -p "Enter tenant ID: " TENANT_ID
        read -p "Enter project ID: " PROJECT_ID
        read -p "Enter task ID: " TASK_ID
        echo -e "${CYAN}Mode: Full filtering (${TENANT_ID}/${PROJECT_ID}/${TASK_ID})${NC}"
        HEADERS+=("-H" "x-tenant-id: $TENANT_ID" "-H" "x-project-id: $PROJECT_ID" "-H" "x-task-id: $TASK_ID")
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}Tips:${NC}"
echo "  - Type 'exit' or 'quit' to end the conversation"
echo "  - Type 'clear' to clear the screen"
echo "  - The agent remembers the last 6 messages for context"
echo ""
echo -e "${GREEN}Chat started. Ask anything!${NC}"
echo ""

while true; do
    # Read user input
    echo -ne "${BLUE}You: ${NC}"
    read -r USER_INPUT

    # Handle special commands
    case "$USER_INPUT" in
        exit|quit)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        clear)
            clear
            echo -e "${GREEN}💬 Interactive Chat with ProcessApp Agent${NC}"
            echo "==========================================="
            echo ""
            continue
            ;;
        "")
            continue
            ;;
    esac

    # Send to agent
    echo -ne "${CYAN}Agent: ${NC}"
    curl -s -X POST $BASE_URL/invocations \
        "${HEADERS[@]}" \
        -H "Content-Type: application/json" \
        -d "{
            \"inputText\": $(echo "$USER_INPUT" | jq -Rs .),
            \"sessionId\": \"$SESSION_ID\"
        }" | while IFS= read -r line; do
            echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
        done

    echo ""
    echo ""
done
