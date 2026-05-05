"""
ProcessApp Agent - Main Entry Point
Version: 2.0.0 - Refactored with clean orchestration

Clean, modular agent implementation using:
- Strands SDK for agent runtime
- Bedrock Knowledge Base for retrieval
- Multi-tenant metadata filtering
"""

import sys
import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from core import AgentOrchestrator, AgentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize configuration and orchestrator
config = AgentConfig()
orchestrator = AgentOrchestrator(config)

# FastAPI app
app = FastAPI(
    title="ProcessApp Agent",
    version="2.0.0",
    description="Multi-tenant RAG agent with metadata filtering"
)


@app.post("/invocations")
async def invocations_endpoint(request: Request):
    """
    Main invocation endpoint for agent requests.

    Request body:
        {
            "inputText": "User question",
            "sessionId": "unique-session-id",
            "metadata": {
                "tenant_id": "1001",
                "project_id": "165",
                "task_id": "174"  // optional
            }
        }

    Response: NDJSON stream
        {"type": "chunk", "data": "word word word "}
        {"type": "complete", "sessionId": "..."}
    """
    try:
        # Parse request
        body = await request.json()
        input_text = body.get('inputText') or body.get('prompt') or body.get('question') or 'Hola'
        session_id = body.get('sessionId', 'default')

        logger.info(f'[Request] Input: "{input_text[:50]}...", Session: {session_id}')

        # Extract metadata
        headers_dict = dict(request.headers)
        metadata = orchestrator.extract_metadata(headers_dict, body)

        # Process request and stream response
        async def generate():
            async for chunk in orchestrator.process_request(input_text, session_id, metadata):
                yield json.dumps(chunk) + "\n"

        return StreamingResponse(generate(), media_type="application/x-ndjson")

    except Exception as e:
        logger.error(f'[Error] Endpoint: {e}', exc_info=True)
        return JSONResponse(
            {"error": "Error procesando solicitud"},
            status_code=500
        )


@app.get("/health")
@app.get("/ping")
async def health_endpoint():
    """
    Health check endpoint.

    Returns agent status and configuration.
    """
    return orchestrator.get_health_status()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ProcessApp Agent",
        "version": "2.0.0",
        "status": "healthy",
        "endpoints": {
            "health": "/health",
            "invocations": "/invocations (POST)"
        },
        "tools": ["retrieve", "http_request"],
        "model": config.model_id
    }


if __name__ == '__main__':
    logger.info(f'✅ ProcessApp Agent v2.0.0 ready on port {config.port}')
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=config.port,
        log_level='warning'
    )
