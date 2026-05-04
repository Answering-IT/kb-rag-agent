"""
ProcessApp Agent - Simplified Bedrock Agent with Strand SDK + retrieve tool
"""

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from strands import Agent
from strands_tools import retrieve, http_request
import uvicorn
from typing import Optional, Dict, Any

# Environment variables
KB_ID = os.environ.get('KB_ID', '')
# CRITICAL: Set KNOWLEDGE_BASE_ID for Strand's retrieve tool
os.environ['KNOWLEDGE_BASE_ID'] = KB_ID

MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
PORT = int(os.environ.get('PORT', '8080'))
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Set AWS_REGION for Bedrock (required by strands)
os.environ['AWS_REGION'] = REGION

print('🚀 ProcessApp Agent (Strand SDK + Bedrock)')
print(f'   Model/Inference Profile: {MODEL_ID}')
print(f'   Region: {REGION}')
print(f'   KB: {KB_ID[:20]}...' if len(KB_ID) > 20 else f'   KB: {KB_ID or "Not configured"}')

# Module-level variable for KB filter (for metadata filtering)
_CURRENT_KB_FILTER: Optional[Dict[str, Any]] = None

# Session storage
_sessions: Dict[str, list] = {}


def remove_thinking_tags(text: str) -> str:
    """Remove <thinking>...</thinking> tags from model responses."""
    import re
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Remove extra blank lines
    return cleaned.strip()


# Create agent with inference profile ID (Strands automatically detects Bedrock models)
# Pass the full inference profile ID (with us. prefix) for on-demand throughput
agent = Agent(
    model=MODEL_ID,
    tools=[retrieve, http_request],
    system_prompt="""Eres un asistente conversacional amigable y útil. Mantienes el contexto de la conversación y recuerdas lo que el usuario te ha dicho.

**Herramientas:**
- `retrieve`: Busca en la base de conocimiento empresarial cuando necesites información específica
- `http_request`: Obtiene contenido de URLs cuando sea necesario

**Comportamiento:**
- Mantén una conversación natural y recuerda el contexto previo
- Usa `retrieve` SOLO cuando el usuario necesite información específica de documentos
- Para conversación general, responde directamente sin buscar
- Sé conciso pero amigable
- Si no sabes algo o no está en tu conocimiento, dilo claramente

Responde en español de forma natural y conversacional."""
)

# FastAPI app
app = FastAPI(title="ProcessApp Agent")

@app.post("/invocations")
async def invocations_endpoint(request: Request):
    """Main invocation endpoint."""
    try:
        body = await request.json()
        input_text = body.get('inputText') or body.get('prompt') or body.get('question') or 'Hola'
        session_id = body.get('sessionId', 'default')

        if DEBUG:
            print(f'[Request] {input_text[:80]}... (session: {session_id})')

        # Set KB filter from metadata
        try:
            from metadata_handler import KBFilterBuilder
            metadata = KBFilterBuilder.extract_from_request(dict(request.headers), body)
            kb_filter = KBFilterBuilder.build_filter(metadata)
            global _CURRENT_KB_FILTER
            _CURRENT_KB_FILTER = kb_filter
        except Exception as e:
            if DEBUG:
                print(f'[Metadata] Error: {e}')

        # Get session history (keep last 6 messages for better context)
        if session_id not in _sessions:
            _sessions[session_id] = []

        # Build conversation history for context
        conversation_context = ""
        if len(_sessions[session_id]) > 0:
            recent_messages = _sessions[session_id][-6:]  # Last 3 exchanges
            for msg in recent_messages:
                role = "Usuario" if msg['role'] == 'user' else "Asistente"
                conversation_context += f"{role}: {msg['content']}\n"

        _sessions[session_id].append({'role': 'user', 'content': input_text})
        if len(_sessions[session_id]) > 8:
            _sessions[session_id] = _sessions[session_id][-8:]

        async def generate():
            try:
                # Set KB filter in environment if present
                global _CURRENT_KB_FILTER
                if _CURRENT_KB_FILTER and DEBUG:
                    print(f'[Filter] Applying: {json.dumps(_CURRENT_KB_FILTER)}')

                # Build enhanced prompt with conversation context and metadata filter
                enhanced_prompt = input_text

                if conversation_context:
                    enhanced_prompt = f"Contexto de conversación reciente:\n{conversation_context}\nUsuario actual: {input_text}"

                if _CURRENT_KB_FILTER:
                    enhanced_prompt += f"""\n\nIMPORTANTE: Si usas 'retrieve', incluye el parámetro 'retrieveFilter':
{json.dumps(_CURRENT_KB_FILTER, indent=2)}"""

                # Call agent with context
                result = agent(enhanced_prompt)

                # Extract response
                response_text = ""
                if hasattr(result, 'output'):
                    response_text = result.output
                elif hasattr(result, 'content'):
                    response_text = result.content
                elif hasattr(result, 'text'):
                    response_text = result.text
                else:
                    response_text = str(result)

                # Remove thinking tags
                response_text = remove_thinking_tags(response_text)

                # Limit size
                if len(response_text) > 4000:
                    response_text = response_text[:4000]

                if DEBUG:
                    print(f'[Response] {len(response_text)} chars')

                # Store full response in session for context
                _sessions[session_id].append({'role': 'assistant', 'content': response_text})

                # Stream response
                words = response_text.split()
                for i in range(0, len(words), 3):
                    chunk = " ".join(words[i:i+3]) + " "
                    yield json.dumps({"type": "chunk", "data": chunk}) + "\n"

                yield json.dumps({"type": "complete", "sessionId": session_id}) + "\n"

            except Exception as e:
                print(f'[Error] {e}')
                import traceback
                traceback.print_exc()

                yield json.dumps({
                    "type": "chunk",
                    "data": "Disculpa, tuve un problema procesando tu pregunta."
                }) + "\n"
                yield json.dumps({"type": "complete", "sessionId": session_id}) + "\n"
            finally:
                _CURRENT_KB_FILTER = None

        return StreamingResponse(generate(), media_type="application/x-ndjson")

    except Exception as e:
        print(f'[Error] Endpoint: {e}')
        return JSONResponse({"error": "Error procesando solicitud"}, status_code=500)



@app.get("/ping")
@app.get("/health")
async def health_endpoint():
    """Health check"""
    return {
        "status": "healthy",
        "model": MODEL_ID,
        "region": REGION,
        "kb_id": KB_ID,
        "tools": ["retrieve", "http_request"],
        "provider": "bedrock",
        "sessions": len(_sessions)
    }

if __name__ == '__main__':
    print(f'✅ Agent ready on port {PORT}')
    if DEBUG:
        print(f'   Model: {MODEL_ID}')
        print(f'   KB ID: {KB_ID}')
        print(f'   Tools: retrieve, http_request')

    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='warning')
