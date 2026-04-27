"""
ProcessApp Agent - Bedrock Agent Core Runtime with Strand SDK

Uses Strand Python SDK for agent orchestration
FastAPI for HTTP server
Compatible with AWS Bedrock Agent Core Runtime protocol
"""

import os
import json
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from strands import Agent, tool
import uvicorn

# Environment variables
KB_ID = os.environ.get('KB_ID', '')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
ECS_BASE_URL = os.environ.get('ECS_BASE_URL', 'https://dev.app.colpensiones.procesapp.com')
PORT = int(os.environ.get('PORT', '8080'))

print('🚀 ProcessApp Agent Core Runtime (Strand SDK)')
print(f'   Model: {MODEL_ID}')
print(f'   KB: {KB_ID or "Not configured"}')
print(f'   Region: {REGION}')
print(f'   Port: {PORT}')

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Create tools for agent
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the ProcessApp knowledge base for relevant information.

    Args:
        query: The search query to find relevant documents

    Returns:
        Relevant information from the knowledge base
    """
    if not KB_ID:
        return "Knowledge base is not configured."

    try:
        print(f'[KB Tool] Searching: {query}')
        kb_response = bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3
                }
            }
        )

        # Extract contexts
        contexts = []
        for result in kb_response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            if content:
                contexts.append(content)

        if contexts:
            print(f'[KB Tool] Found {len(contexts)} results')
            return "\n\n---\n\n".join(contexts[:2])  # Return top 2 results
        else:
            return "No relevant information found in the knowledge base."

    except Exception as e:
        print(f'[KB Tool] Error: {e}')
        return f"Error searching knowledge base: {str(e)}"


@tool
def get_project_info(org_id: str, project_id: str) -> str:
    """
    Get detailed information about a specific project from the ECS service.

    Args:
        org_id: The organization ID (e.g., "1")
        project_id: The project ID (e.g., "123")

    Returns:
        Project information including name, budget, status, and other details
    """
    try:
        import urllib3
        http = urllib3.PoolManager()

        print(f'[ProjectInfo Tool] Fetching project - orgId: {org_id}, projectId: {project_id}')

        # Build URL to ECS service
        url = f"{ECS_BASE_URL}/organization/{org_id}/projects/{project_id}"

        print(f'[ProjectInfo Tool] Calling: {url}')

        # Call ECS service
        response = http.request('GET', url, timeout=10.0)

        if response.status == 200:
            project_data = json.loads(response.data.decode('utf-8'))
            print(f'[ProjectInfo Tool] Success - Project: {project_data.get("name", "Unknown")}')

            # Format response for the agent
            return json.dumps(project_data, indent=2)
        else:
            error_msg = f"HTTP {response.status}: {response.data.decode('utf-8')}"
            print(f'[ProjectInfo Tool] Error: {error_msg}')
            return f"Error fetching project info: {error_msg}"

    except Exception as e:
        print(f'[ProjectInfo Tool] Exception: {e}')
        import traceback
        print(f'[ProjectInfo Tool] Traceback: {traceback.format_exc()}')
        return f"Error calling ECS service: {str(e)}"

# Create Strand Agent with tools
agent = Agent(
    model=MODEL_ID,
    tools=[search_knowledge_base, get_project_info]
)

# Create FastAPI app
app = FastAPI(title="ProcessApp Agent Core Runtime")

@app.post("/invocations")
async def invocations_endpoint(request: Request):
    """
    Main invocation endpoint for Agent Core Runtime
    Compatible with Bedrock Agent Core protocol
    """
    try:
        body = await request.json()
        input_text = body.get('inputText') or body.get('prompt') or body.get('question') or 'Hello'
        session_id = body.get('sessionId', 'unknown')

        print(f'\n[API] Request: {input_text}')
        print(f'[API] Session: {session_id}')

        # Use Strand agent - it returns AgentResult object
        async def generate_response():
            try:
                # Call agent synchronously (Strand agents are sync)
                result = agent(input_text)

                # Convert AgentResult to string
                # Try different attributes that Strand SDK might use
                if hasattr(result, 'output'):
                    response_text = result.output
                elif hasattr(result, 'content'):
                    response_text = result.content
                elif hasattr(result, 'text'):
                    response_text = result.text
                else:
                    # Fallback to string conversion
                    response_text = str(result)

                print(f'[API] Response type: {type(result)}')
                print(f'[API] Response length: {len(response_text)} chars')

                # Stream response in chunks
                words = response_text.split()
                chunk_size = 10
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size]) + " "
                    yield json.dumps({"type": "chunk", "data": chunk}) + "\n"

                # Completion signal
                yield json.dumps({"type": "complete", "sessionId": session_id}) + "\n"

            except Exception as e:
                print(f'[API] Error in generator: {e}')
                import traceback
                print(f'[API] Traceback: {traceback.format_exc()}')
                yield json.dumps({"type": "error", "message": str(e)}) + "\n"

        return StreamingResponse(
            generate_response(),
            media_type="application/x-ndjson"
        )

    except Exception as e:
        print(f'[API] Error: {str(e)}')
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )

@app.get("/ping")
@app.get("/health")
async def health_endpoint():
    """Health check endpoint - required by Agent Core Runtime"""
    return {
        "status": "healthy",
        "runtime": "ProcessApp Agent V2 (Strand SDK)",
        "kb_id": KB_ID,
        "model": MODEL_ID,
        "sdk": "strands-agents"
    }

if __name__ == '__main__':
    print(f'\n✅ Starting FastAPI server on port {PORT}')
    print(f'   Endpoint: POST /invocations')
    print(f'   Health: GET /health, GET /ping')
    print(f'   SDK: Strand Python SDK\n')

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=PORT,
        log_level='info'
    )
