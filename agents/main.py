"""
ProcessApp Agent - Simplified Bedrock Agent with Strand SDK
"""

import os
import json
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from strands import Agent, tool
from strands_tools import http_request
import uvicorn
from pathlib import Path
from typing import Optional, Dict, Any

# Environment variables
KB_ID = os.environ.get('KB_ID', '')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
PORT = int(os.environ.get('PORT', '8080'))

print('🚀 ProcessApp Agent (Strand SDK)')
print(f'   Model: {MODEL_ID}')
print(f'   KB: {KB_ID or "Not configured"}')

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

# Module-level variable for KB filter
_CURRENT_KB_FILTER: Optional[Dict[str, Any]] = None

# Load normative framework (keep first 2000 chars only)
NORMATIVE_FRAMEWORK_PATH = Path(__file__).parent / 'marco_normativo_colpensiones.md'
NORMATIVE_FRAMEWORK = ""
try:
    if NORMATIVE_FRAMEWORK_PATH.exists():
        full_content = NORMATIVE_FRAMEWORK_PATH.read_text(encoding='utf-8')
        NORMATIVE_FRAMEWORK = full_content[:2000]  # Truncate at load time
        print(f'✅ Loaded normative framework: {len(NORMATIVE_FRAMEWORK)} chars')
except Exception as e:
    print(f'⚠️  Error loading framework: {e}')

# Session storage (simple dict, no complex management)
_sessions: Dict[str, list] = {}


def remove_thinking_tags(text: str) -> str:
    """Remove <thinking>...</thinking> tags from model responses."""
    import re
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Remove extra blank lines
    return cleaned.strip()


# Tools
@tool
def search_knowledge_base(query: str) -> str:
    """Search ProcessApp knowledge base with metadata filters."""
    if not KB_ID:
        print("[KB] Not configured")
        return "No hay información disponible en este momento."

    try:
        print(f'[KB] Query: {query[:50]}...')

        config = {'vectorSearchConfiguration': {'numberOfResults': 2}}

        global _CURRENT_KB_FILTER
        if _CURRENT_KB_FILTER:
            config['vectorSearchConfiguration']['filter'] = _CURRENT_KB_FILTER

        response = bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration=config
        )

        results = []
        for r in response.get('retrievalResults', []):
            content = r.get('content', {}).get('text', '')
            if content:
                results.append(content[:1000])  # Limit each result

        if results:
            print(f'[KB] Found {len(results)} results')
            return "\n\n---\n\n".join(results)

        print("[KB] No results")
        return "No encontré información relevante en la base de conocimiento."

    except Exception as e:
        print(f'[KB] Error: {e}')
        return "No pude acceder a la base de conocimiento en este momento."




@tool
def consult_normative_document(query: str) -> str:
    """Consulta normativa pensional colombiana (leyes, decretos)."""
    print(f'[Normative] Query: {query[:50]}...')

    if not NORMATIVE_FRAMEWORK:
        print("[Normative] Framework not loaded")
        return "El índice normativo no está disponible. Puedo intentar ayudarte de otra manera."

    return f"""**Índice normativo sobre:** {query}

{NORMATIVE_FRAMEWORK}

**Instrucciones:** Busca el documento relevante en el índice anterior y proporciona al usuario la información en formato Markdown con las URLs oficiales."""


# Create agent with simple system prompt
agent = Agent(
    model=MODEL_ID,
    tools=[search_knowledge_base, consult_normative_document, http_request],
    system_prompt="""Eres un asistente experto en normativa pensional colombiana (Colpensiones).

**Herramientas:**
- `consult_normative_document`: Índice de leyes/decretos/jurisprudencia
- `search_knowledge_base`: Base de conocimiento ProcessApp
- `http_request`: Obtener contenido de URLs oficiales

**Protocolo:**
1. Para preguntas sobre normativa: usa `consult_normative_document` primero
2. Proporciona siempre: nombre del documento, año, URL oficial, resumen
3. Responde en Markdown bien formateado (encabezados ##, listas -, negritas **, emojis 📋🔗⚠️)

**Ejemplo de respuesta:**

## Decreto 1558 de 2024 - Ahorro Individual

**Tema:** Ahorro voluntario complementario en la reforma pensional

**Puntos clave:**
- Reglamenta el componente de ahorro voluntario
- Establece requisitos para administradoras
- Define condiciones de retiro

**Consultar:**
- 🔗 [Función Pública](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=247845)

---

**Tono:** Profesional y claro. Recuerda el contexto de la conversación actual."""
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

        print(f'[Request] {input_text[:80]}... (session: {session_id})')

        # Set KB filter from metadata
        try:
            from metadata_handler import KBFilterBuilder
            metadata = KBFilterBuilder.extract_from_request(dict(request.headers), body)
            kb_filter = KBFilterBuilder.build_filter(metadata)
            global _CURRENT_KB_FILTER
            _CURRENT_KB_FILTER = kb_filter
        except Exception as e:
            print(f'[Metadata] Error: {e}')

        # Get session history (simple: keep last 4 messages)
        if session_id not in _sessions:
            _sessions[session_id] = []
        _sessions[session_id].append({'role': 'user', 'content': input_text[:200]})
        if len(_sessions[session_id]) > 4:
            _sessions[session_id] = _sessions[session_id][-4:]

        async def generate():
            try:
                # Call agent
                result = agent(input_text)

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

                # Remove thinking tags before sending to user
                response_text = remove_thinking_tags(response_text)

                # Limit response size
                if len(response_text) > 4000:
                    response_text = response_text[:4000] + "\n\n[Respuesta truncada por límite de tokens]"
                    print(f'[Response] Truncated to 4000 chars')

                print(f'[Response] {len(response_text)} chars')

                # Store in session
                _sessions[session_id].append({'role': 'assistant', 'content': response_text[:200]})

                # Stream response with smaller chunks (3 words at a time for lower latency)
                words = response_text.split()
                for i in range(0, len(words), 3):
                    chunk = " ".join(words[i:i+3]) + " "
                    yield json.dumps({"type": "chunk", "data": chunk}) + "\n"

                yield json.dumps({"type": "complete", "sessionId": session_id}) + "\n"

            except Exception as e:
                print(f'[Error] {e}')
                import traceback
                traceback.print_exc()

                # User-friendly error, log full details
                yield json.dumps({
                    "type": "chunk",
                    "data": "Disculpa, tuve un problema procesando tu pregunta. ¿Puedes intentarlo de nuevo?"
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
        "tools": ["search_knowledge_base", "consult_normative_document", "http_request"],
        "framework_loaded": bool(NORMATIVE_FRAMEWORK),
        "sessions": len(_sessions)
    }

if __name__ == '__main__':
    print(f'✅ Starting ProcessApp Agent on port {PORT}')
    print(f'   Model: {MODEL_ID}')
    print(f'   Tools: search_knowledge_base, consult_normative_document, http_request')
    print(f'   Framework: {"✅" if NORMATIVE_FRAMEWORK else "❌"}')

    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='info')
