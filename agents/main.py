"""
ProcessApp Agent - Bedrock Agent Core Runtime with Strand SDK

Uses Strand Python SDK for agent orchestration
FastAPI for HTTP server
Compatible with AWS Bedrock Agent Core Runtime protocol
"""

import os
import json
import boto3
import re
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from strands import Agent, tool
from strands_tools import http_request
import uvicorn
from pathlib import Path

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

# Load normative framework for Colpensiones
NORMATIVE_FRAMEWORK_PATH = Path(__file__).parent / 'marco_normativo_colpensiones.md'
NORMATIVE_FRAMEWORK = ""
try:
    if NORMATIVE_FRAMEWORK_PATH.exists():
        NORMATIVE_FRAMEWORK = NORMATIVE_FRAMEWORK_PATH.read_text(encoding='utf-8')
        print(f'✅ Loaded Colpensiones normative framework index')
        print(f'   Size: {len(NORMATIVE_FRAMEWORK)} chars')
    else:
        print(f'⚠️  Normative framework not found at {NORMATIVE_FRAMEWORK_PATH}')
        print(f'   Current dir: {Path(__file__).parent}')
        print(f'   Files: {list(Path(__file__).parent.glob("*"))}')
except Exception as e:
    print(f'⚠️  Error loading normative framework: {e}')
    import traceback
    traceback.print_exc()

# Utility function to filter thinking tags from model responses
def remove_thinking_tags(text: str) -> str:
    """
    Remove <thinking>...</thinking> tags from model responses.
    These are internal model reasoning that shouldn't be shown to users.
    """
    # Remove thinking tags and their content
    cleaned_text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove any leftover empty lines
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    return cleaned_text.strip()

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
    Get information about a ProcessApp project. Returns the URL to fetch project data.
    After getting the URL, use the http_request tool to fetch the actual data.

    Args:
        org_id: The organization ID (e.g., "1")
        project_id: The project ID (e.g., "123")

    Returns:
        Instructions for fetching project information with the http_request tool
    """
    print(f'[ProjectInfo Tool] orgId: {org_id}, projectId: {project_id}')

    url = f"{ECS_BASE_URL}/organization/{org_id}/projects/{project_id}"

    return f"""To fetch this project's information, use the http_request tool with:
- URL: {url}
- Method: GET

This will return the project details including name, budget, status, and other information."""


@tool
def consult_normative_document(query: str) -> str:
    """
    Consulta el índice COMPLETO de leyes, decretos, circulares y jurisprudencia de pensiones colombianas.

    Este índice incluye TODA la normativa de Colpensiones:
    - Ley 2381/2024, Decreto 1558/2024, Decreto 1225/2024, Decreto 514/2025
    - Ley 100/1993, Ley 797/2003, Ley 1480/2011
    - Decretos históricos y actuales
    - Circulares de Superintendencia Financiera
    - Jurisprudencia de Corte Constitucional y Corte Suprema

    SIEMPRE usa esta herramienta cuando el usuario pregunte sobre normativa pensional.
    NUNCA digas "no tengo acceso" - esta herramienta te da acceso completo.

    Args:
        query: Ley, decreto o tema normativo a consultar
               Ejemplos: "Decreto 1558 de 2024", "Ahorro Individual", "Ley 2381"

    Returns:
        Índice completo con URLs oficiales, descripción de documentos y advertencias
    """
    try:
        print(f'[Normative Tool] Query: {query}')

        if not NORMATIVE_FRAMEWORK:
            error_msg = """⚠️ ERROR CRÍTICO: Marco normativo no cargado.

**Diagnóstico:**
- El archivo marco_normativo_colpensiones.md no está disponible
- Posible problema en el contenedor Docker
- Contactar al administrador del sistema

**Archivos esperados:**
- /app/marco_normativo_colpensiones.md

**Solución temporal:**
- Verificar que el Dockerfile incluya: COPY marco_normativo_colpensiones.md .
- Re-desplegar el agente"""

            print(f'[Normative Tool] ERROR: Framework not loaded')
            print(f'[Normative Tool] Path: {NORMATIVE_FRAMEWORK_PATH}')
            print(f'[Normative Tool] Exists: {NORMATIVE_FRAMEWORK_PATH.exists()}')

            return error_msg

        print(f'[Normative Tool] Framework loaded: {len(NORMATIVE_FRAMEWORK)} chars')

        # Return the full framework with context
        return f"""# 📚 Marco Normativo de Colpensiones - Índice Completo

**Tu consulta:** {query}

---

{NORMATIVE_FRAMEWORK}

---

## 🎯 Cómo usar esta información:

1. **Identifica** el documento relevante en el índice anterior
2. **Extrae** las URLs oficiales (Fuente oficial primaria y alternativas)
3. **Proporciona** al usuario:
   - Nombre completo del documento
   - Tema/descripción
   - URLs oficiales para consultar
   - Advertencias (⚠️) si existen
   - Contexto legal relevante

4. **Opcional:** Si necesitas el texto completo del documento, usa `http_request` con las URLs oficiales

5. **IMPORTANTE:** Devuelve tu respuesta al usuario en formato Markdown bien estructurado con:
   - Encabezados (##)
   - Listas con viñetas
   - Negritas para términos importantes
   - Enlaces en formato [texto](url)
   - Saltos de línea entre secciones
   - Emojis para mejor legibilidad

## ✅ Recuerda:

- Este índice contiene TODA la normativa - nunca digas "no tengo acceso"
- Para documentos muy recientes (2025-2026), menciona que pueden estar en consolidación
- Siempre cita las fuentes oficiales primarias
"""

    except Exception as e:
        error_msg = f"""⚠️ Error al consultar el marco normativo.

**Error técnico:** {str(e)}

**Posibles causas:**
- Problema de lectura del archivo
- Error en el procesamiento
- Problema de memoria

**Información de debug:**
- Query: {query}
- Path: {NORMATIVE_FRAMEWORK_PATH}

Contactar al administrador del sistema."""

        print(f'[Normative Tool] Exception: {e}')
        import traceback
        traceback.print_exc()

        return error_msg


# Create Strand Agent with tools
agent = Agent(
    model=MODEL_ID,
    tools=[
        # search_knowledge_base,  # Disabled for now
        # get_project_info,       # Disabled for now
        consult_normative_document,
        http_request  # Strands official HTTP tool
    ],
    system_prompt="""Eres un asistente experto en normativa pensional colombiana (Colpensiones).

**🔧 Herramientas disponibles:**

1. **consult_normative_document** - Accede al índice completo de leyes/decretos/jurisprudencia colombiana de pensiones
2. **http_request** - Obtiene contenido desde URLs oficiales del gobierno

**📋 PROTOCOLO OBLIGATORIO para responder preguntas normativas:**

Cuando el usuario pregunte sobre leyes, decretos o regulaciones de pensiones:

1. **SIEMPRE** usa `consult_normative_document` primero
   - Esta herramienta contiene el índice COMPLETO del marco normativo
   - Incluye: Ley 2381/2024, Decreto 1558/2024, Decreto 1225/2024, Decreto 514/2025, y TODOS los decretos y leyes
   - ⚠️ NUNCA digas "no tengo acceso" o "no puedo consultar" - SÍ TIENES ACCESO COMPLETO

2. **Opcional**: Si necesitas el texto completo del documento, usa `http_request` con las URLs oficiales que obtuviste del índice

3. **Siempre proporciona**:
   - Nombre completo de la ley/decreto
   - Número y año
   - URL oficial donde se puede consultar
   - Resumen del contenido relevante a la pregunta
   - Advertencias marcadas con ⚠️ si existen

**✅ Ejemplos de temas que SÍ PUEDES responder (tienes el índice completo):**
- Ley 2381 de 2024 (Reforma Pensional)
- Decreto 1558 de 2024 (Ahorro Individual) ← SÍ ESTÁ EN EL ÍNDICE
- Decreto 1225 de 2024 (Implementación)
- Decreto 514 de 2025 (Compilación)
- Ley 100 de 1993 (Sistema General)
- Circular 016 de 2016 (Protección al consumidor)
- Jurisprudencia (Sentencias C-258/2020, SL379/2021, etc.)
- Y MUCHOS MÁS - consulta el índice con la herramienta

**📝 FORMATO DE RESPUESTA OBLIGATORIO:**

SIEMPRE usa Markdown con formato claro y visual:

```markdown
## [Título del Decreto/Ley]

**Tema:** [Descripción breve]

**Contenido principal:**
- Punto 1
- Punto 2
- Punto 3

**Dónde consultarlo:**
- 🔗 Fuente oficial primaria: [URL]
- 🔗 Fuente alternativa: [URL] (si aplica)

**Notas importantes:**
⚠️ [Advertencias si existen]

---
*Fuente: [Citar fuente oficial]*
```

**🎨 Reglas de formato (OBLIGATORIAS):**

1. ✅ USA encabezados (##, ###) para estructura
2. ✅ USA listas con viñetas (-) o numeradas (1.)
3. ✅ USA **negritas** para destacar términos importantes
4. ✅ USA líneas horizontales (---) para separar secciones
5. ✅ USA emojis apropiados (📋, 🔗, ⚠️, ✅, 📚) para mejor legibilidad
6. ✅ Incluye saltos de línea entre párrafos
7. ✅ URLs en formato markdown: [Texto descriptivo](URL)
8. ❌ NUNCA devuelvas texto plano sin formato
9. ❌ NUNCA pongas todo en un solo párrafo

**🚫 PROHIBICIONES:**

- ❌ NUNCA digas "no tengo acceso a esa información" sobre normativa - SÍ tienes acceso vía consult_normative_document
- ❌ NUNCA digas "no puedo consultar" - SÍ puedes consultar usando las herramientas
- ❌ NUNCA devuelvas respuestas sin formato markdown
- ❌ NUNCA omitas los saltos de línea o el formato visual

**Ejemplo de respuesta CORRECTA:**

```
## Decreto 1558 de 2024 - Ahorro Individual

**Tema:** Modifica el Decreto 2555 de 2010 y adiciona normas para el Componente Complementario de Ahorro Individual dentro de la reforma pensional.

**Aspectos clave:**
- Reglamenta el ahorro voluntario complementario
- Establece requisitos para las administradoras
- Define condiciones de retiro y beneficios fiscales

**Dónde consultarlo:**
- 🔗 **Fuente oficial primaria:** https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=247845
- 🔗 **Presidencia de la República:** https://dapre.presidencia.gov.co/normativa/normativa/DECRETO%201558%20DEL%2020%20DE%20DICIEMBRE%20DE%202024.pdf

**Contexto:**
Este decreto es parte de la implementación de la Ley 2381 de 2024 (Reforma Pensional) y específicamente regula el pilar de ahorro individual complementario.

---
*Fuente: Función Pública - Sistema Único de Información Normativa*
```

**💬 Tono de comunicación:**
- Profesional pero accesible
- Explica el contexto legal en español claro
- Si el documento es muy reciente (2025-2026), menciona que puede estar en consolidación en bases de datos"""
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
                print(f'[API] Raw response length: {len(response_text)} chars')

                # Filter thinking tags before sending to user
                response_text = remove_thinking_tags(response_text)

                print(f'[API] Cleaned response length: {len(response_text)} chars')

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
        "runtime": "ProcessApp Agent V3 - Normative Consultant (Strand SDK)",
        "model": MODEL_ID,
        "tools_active": ["consult_normative_document", "http_request"],
        "tools_disabled": ["search_knowledge_base", "get_project_info"],
        "normative_framework_loaded": bool(NORMATIVE_FRAMEWORK)
    }

if __name__ == '__main__':
    print(f'\n✅ Starting FastAPI server on port {PORT}')
    print(f'   Mode: Normative Consultant (Colpensiones)')
    print(f'   Endpoint: POST /invocations')
    print(f'   Health: GET /health, GET /ping')
    print(f'   SDK: Strand Python SDK + strands-agents-tools')
    print(f'   Active Tools: consult_normative_document, http_request')
    print(f'   Framework: {"✅ Loaded" if NORMATIVE_FRAMEWORK else "❌ Not loaded"}\n')

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=PORT,
        log_level='info'
    )
