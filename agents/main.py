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
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from threading import Lock
from metadata_handler import KBFilterBuilder, RequestMetadata

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

# Module-level variable to pass KB filter to tools
# This is necessary because Strand SDK tools don't receive context parameters
_CURRENT_KB_FILTER: Optional[Dict[str, Any]] = None

# Session management configuration
CONVERSATION_WINDOW_SIZE = 20  # Keep last 20 messages (10 exchanges)
SESSION_TTL_MINUTES = 30  # Expire idle sessions after 30 minutes
TOOL_RESPONSE_MAX_CHARS = 3000  # Truncate large tool responses
MAX_RESPONSE_CHARS = 5000  # Maximum response size before truncation

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


# Session Management Classes
@dataclass
class ConversationMessage:
    """Single message in conversation history"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SessionConversation:
    """Stores conversation state for a session"""
    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    truncation_count: int = 0

    def is_expired(self) -> bool:
        """Check if session has expired"""
        age = datetime.now() - self.last_activity
        return age > timedelta(minutes=SESSION_TTL_MINUTES)

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def add_message(self, role: str, content: str, is_truncated: bool = False):
        """Add message with sliding window enforcement"""
        message = ConversationMessage(role=role, content=content)
        self.messages.append(message)
        self.message_count += 1

        if is_truncated:
            self.truncation_count += 1

        # Sliding window: keep only last CONVERSATION_WINDOW_SIZE messages
        if len(self.messages) > CONVERSATION_WINDOW_SIZE:
            removed = self.messages.pop(0)
            print(f'[SlidingWindow] Dropped oldest message: {removed.role} from {removed.timestamp}')

        self.update_activity()

    def get_recent_messages(self, count: int = 6) -> List[ConversationMessage]:
        """Get last N messages for context"""
        return self.messages[-count:]


class ConversationStore:
    """Thread-safe in-memory store for sessions"""

    def __init__(self):
        self._sessions: Dict[str, SessionConversation] = {}
        self._lock = Lock()

    def get_or_create_session(self, session_id: str) -> SessionConversation:
        """Get existing session or create new one"""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionConversation(session_id=session_id)
                print(f'[Session] Created: {session_id}')

            session = self._sessions[session_id]
            session.update_activity()
            return session

    def add_message(self, session_id: str, role: str, content: str, is_truncated: bool = False):
        """Add message to session with sliding window"""
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.add_message(role, content, is_truncated)
                print(f'[Session] Message added: {session_id} | Total: {session.message_count} | Window: {len(session.messages)}')

    def get_history(self, session_id: str) -> List[ConversationMessage]:
        """Get conversation history for session"""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id].messages.copy()
            return []

    def cleanup_expired(self) -> int:
        """Remove expired sessions"""
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired:
                session = self._sessions.pop(sid)
                print(f'[Session] Expired & removed: {sid} | Messages: {session.message_count}')
            return len(expired)

    def get_stats(self, session_id: str) -> Dict:
        """Get session statistics"""
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                return {
                    'session_id': session_id,
                    'message_count': session.message_count,
                    'window_size': len(session.messages),
                    'truncation_count': session.truncation_count,
                    'age_minutes': round((datetime.now() - session.last_activity).total_seconds() / 60, 1)
                }
            return {}


# Initialize global conversation store
conversation_store = ConversationStore()


# Helper Functions
def truncate_content(content: str, max_chars: int, label: str) -> tuple:
    """
    Truncate large content to prevent token overflow.

    Returns (truncated_content, was_truncated)
    """
    if len(content) > max_chars:
        truncated = content[:max_chars] + f"\n\n[{label} truncated: {len(content) - max_chars} chars omitted]"
        print(f'[Truncation] {label}: {len(content)} -> {max_chars} chars')
        return truncated, True
    return content, False


def format_conversation_context(messages: List[ConversationMessage]) -> str:
    """
    Format recent conversation history as context for the agent.
    Only includes last 6 messages to keep token count reasonable.
    """
    if not messages:
        return ""

    recent = messages[-6:]  # Last 6 messages (3 exchanges)
    formatted = "\n\n--- RECENT CONVERSATION CONTEXT ---\n\n"
    for msg in recent:
        prefix = "Usuario:" if msg.role == "user" else "Asistente:"
        # Truncate each message to avoid huge context
        content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
        formatted += f"{prefix}\n{content}\n\n"
    formatted += "--- FIN CONTEXTO ---\n\n"

    return formatted


# Create tools for agent
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the ProcessApp knowledge base for relevant information.

    Automatically applies metadata filters for tenant isolation.
    Returns top 2 most relevant results.

    Args:
        query: The search query to find relevant documents

    Returns:
        Relevant information from the knowledge base
    """
    if not KB_ID:
        return "Knowledge base is not configured."

    try:
        print(f'[KB Tool] Searching: {query}')

        # Build retrieval configuration
        retrieval_config = {
            'vectorSearchConfiguration': {
                'numberOfResults': 3
            }
        }

        # Apply metadata filter if present (from module-level variable)
        global _CURRENT_KB_FILTER
        if _CURRENT_KB_FILTER:
            retrieval_config['vectorSearchConfiguration']['filter'] = _CURRENT_KB_FILTER
            print(f'[KB Tool] Applying metadata filter: {_CURRENT_KB_FILTER}')
        else:
            print('[KB Tool] No metadata filter - unrestricted search')

        # Call Bedrock KB retrieve
        kb_response = bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration=retrieval_config
        )

        # Extract contexts
        contexts = []
        for result in kb_response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            score = result.get('score', 0.0)

            # Optional: Log metadata from results
            metadata = result.get('metadata', {})
            if metadata:
                print(f'[KB Tool] Result metadata: {metadata}')

            if content:
                contexts.append(f"[Score: {score:.2f}]\n{content}")

        if contexts:
            print(f'[KB Tool] Found {len(contexts)} results')
            return "\n\n---\n\n".join(contexts[:2])  # Return top 2 results
        else:
            return "No relevant information found in the knowledge base."

    except Exception as e:
        print(f'[KB Tool] Error: {e}')
        import traceback
        print(f'[KB Tool] Traceback: {traceback.format_exc()}')
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

        # Truncate framework to prevent token overflow (keep first 4000 chars)
        truncated_framework, was_truncated = truncate_content(
            NORMATIVE_FRAMEWORK,
            4000,  # ~1000 tokens (more aggressive to prevent model limit)
            "Normative Framework"
        )

        truncation_note = ""
        if was_truncated:
            truncation_note = "\n\n⚠️ **Nota:** El índice ha sido truncado. Si no encuentras el documento específico, usa el tool `http_request` para consultar las URLs oficiales directamente.\n"

        # Return the truncated framework with context
        return f"""# 📚 Marco Normativo de Colpensiones - Índice

**Tu consulta:** {query}

---

{truncated_framework}

---{truncation_note}

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
        search_knowledge_base,      # ✅ ENABLED with metadata filtering
        # get_project_info,         # Still disabled
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
- Si el documento es muy reciente (2025-2026), menciona que puede estar en consolidación en bases de datos

**🧠 MEMORIA DE CONVERSACIÓN:**

IMPORTANTE: Puedes y DEBES recordar el contexto de la conversación actual.

✅ **SÍ puedes recordar:**
- Información que el usuario comparte en la sesión actual (nombres, empresas, proyectos)
- Preguntas anteriores del usuario en la misma sesión
- Contexto de la conversación para dar respuestas más relevantes
- Referencias a temas discutidos previamente en esta sesión

❌ **NO almacenes de forma permanente:**
- Datos sensibles como números de identificación, cuentas bancarias
- Información confidencial del usuario fuera de esta sesión

**Ejemplo correcto:**
- Usuario: "Mi nombre es Carlos y trabajo en Colpensiones"
- Asistente: [RECORDAR: nombre=Carlos, empresa=Colpensiones]
- Usuario: "¿Cuál es mi nombre?"
- Asistente: "Tu nombre es Carlos y trabajas en Colpensiones"

La memoria de conversación mejora la experiencia del usuario. Úsala activamente."""
)

# Create FastAPI app
app = FastAPI(title="ProcessApp Agent Core Runtime")

@app.on_event("startup")
async def startup_event():
    """Initialize cleanup task on startup"""
    print('[Startup] Initializing conversation cleanup...')

    def cleanup_loop():
        """Background cleanup for expired sessions"""
        import time
        while True:
            try:
                time.sleep(30)  # Run every 30 seconds
                expired_count = conversation_store.cleanup_expired()
                if expired_count > 0:
                    print(f'[Cleanup] Removed {expired_count} expired sessions')
            except Exception as e:
                print(f'[Cleanup] Error: {e}')

    # Start cleanup in daemon thread
    import threading
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print('[Startup] Cleanup task started')


@app.post("/invocations")
async def invocations_endpoint(request: Request):
    """
    Main invocation endpoint with:
    - Metadata filtering for KB retrieval
    - Conversation memory management with sliding window
    - Token limit handling

    Compatible with Bedrock Agent Core protocol.
    """
    try:
        # Parse request
        body = await request.json()
        input_text = body.get('inputText') or body.get('prompt') or body.get('question') or 'Hello'
        session_id = body.get('sessionId', 'unknown')

        # Extract headers for metadata
        headers = dict(request.headers)

        print(f'\n[API] Request: {input_text[:100]}...')
        print(f'[API] Session: {session_id}')

        # === PART A: Metadata Filtering ===

        # Extract metadata from request
        metadata = KBFilterBuilder.extract_from_request(headers, body)

        # Build KB filter
        kb_filter = KBFilterBuilder.build_filter(metadata)

        # Set global filter for search_knowledge_base tool
        global _CURRENT_KB_FILTER
        _CURRENT_KB_FILTER = kb_filter

        # === PART B: Conversation Management ===

        # Get or create conversation session
        session = conversation_store.get_or_create_session(session_id)

        # Retrieve conversation history
        history = conversation_store.get_history(session_id)

        # Build enriched system prompt with conversation context
        enriched_system_prompt = agent.system_prompt
        if history:
            context = format_conversation_context(history)
            enriched_system_prompt = f"""{enriched_system_prompt}

{context}

Recuerda este contexto al responder la pregunta actual."""

        # Add user message to conversation
        conversation_store.add_message(session_id, "user", input_text)

        # Log session stats
        stats = conversation_store.get_stats(session_id)
        print(f'[Session] Stats: {stats}')

        async def generate_response():
            try:
                # Create temporary agent with enriched prompt for this request
                from strands import Agent as StrandAgent
                temp_agent = StrandAgent(
                    model=MODEL_ID,
                    tools=[
                        search_knowledge_base,  # ✅ Now enabled with metadata filtering
                        consult_normative_document,
                        http_request
                    ],
                    system_prompt=enriched_system_prompt
                )

                # Call agent
                result = temp_agent(input_text)

                # Extract response text
                if hasattr(result, 'output'):
                    response_text = result.output
                elif hasattr(result, 'content'):
                    response_text = result.content
                elif hasattr(result, 'text'):
                    response_text = result.text
                else:
                    response_text = str(result)

                print(f'[API] Raw response: {len(response_text)} chars')

                # Truncate if needed
                truncated_response, was_truncated = truncate_content(
                    response_text,
                    MAX_RESPONSE_CHARS,
                    "Response"
                )

                # Filter thinking tags
                response_text = remove_thinking_tags(truncated_response)

                print(f'[API] Final response: {len(response_text)} chars (truncated: {was_truncated})')

                # Add assistant message to conversation (store truncated version)
                conversation_store.add_message(
                    session_id,
                    "assistant",
                    response_text[:1000],  # Store first 1000 chars only
                    is_truncated=was_truncated
                )

                # Stream response in chunks
                words = response_text.split()
                chunk_size = 10
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size]) + " "
                    yield json.dumps({"type": "chunk", "data": chunk}) + "\n"

                # Completion signal with stats
                final_stats = conversation_store.get_stats(session_id)
                yield json.dumps({
                    "type": "complete",
                    "sessionId": session_id,
                    "stats": final_stats,
                    "metadata_filtered": bool(kb_filter)
                }) + "\n"

            except Exception as e:
                print(f'[API] Error: {e}')
                import traceback
                print(f'[API] Traceback: {traceback.format_exc()}')

                # Store error message
                try:
                    error_msg = f"Error: {str(e)[:200]}"
                    conversation_store.add_message(session_id, "assistant", error_msg)
                except:
                    pass

                yield json.dumps({"type": "error", "message": str(e)}) + "\n"
            finally:
                # Clear global filter after request
                _CURRENT_KB_FILTER = None

        return StreamingResponse(
            generate_response(),
            media_type="application/x-ndjson"
        )

    except Exception as e:
        print(f'[API] Error in endpoint: {str(e)}')
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


@app.get("/sessions/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get statistics for a specific session"""
    stats = conversation_store.get_stats(session_id)
    if not stats:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return stats


@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    with conversation_store._lock:
        sessions = []
        for sid, session in conversation_store._sessions.items():
            sessions.append({
                'session_id': sid,
                'message_count': session.message_count,
                'window_size': len(session.messages),
                'truncations': session.truncation_count,
                'age_minutes': round((datetime.now() - session.last_activity).total_seconds() / 60, 1),
                'expired': session.is_expired()
            })

    return {
        'total_sessions': len(sessions),
        'sessions': sessions
    }

@app.get("/ping")
@app.get("/health")
async def health_endpoint():
    """Health check with enhanced status"""
    with conversation_store._lock:
        active_sessions = len(conversation_store._sessions)

    return {
        "status": "healthy",
        "runtime": "ProcessApp Agent V3 - Enhanced (Strand SDK)",
        "model": MODEL_ID,
        "tools_active": [
            "search_knowledge_base",      # ✅ NOW ENABLED
            "consult_normative_document",
            "http_request"
        ],
        "tools_disabled": ["get_project_info"],
        "normative_framework_loaded": bool(NORMATIVE_FRAMEWORK),
        "enhancements": {
            "metadata_filtering": True,
            "conversation_management": True,
            "token_limit_handling": True
        },
        "conversation_config": {
            "window_size": CONVERSATION_WINDOW_SIZE,
            "session_ttl_minutes": SESSION_TTL_MINUTES,
            "active_sessions": active_sessions,
            "max_response_chars": MAX_RESPONSE_CHARS,
            "tool_response_max_chars": TOOL_RESPONSE_MAX_CHARS
        }
    }

if __name__ == '__main__':
    print(f'\n✅ Starting FastAPI server on port {PORT}')
    print(f'   Mode: Enhanced Normative Consultant (Colpensiones)')
    print(f'   Endpoints:')
    print(f'     - POST /invocations (main agent endpoint)')
    print(f'     - GET /health, GET /ping (health checks)')
    print(f'     - GET /sessions (list active sessions)')
    print(f'     - GET /sessions/{{id}}/stats (session details)')
    print(f'   SDK: Strand Python SDK + strands-agents-tools')
    print(f'   Active Tools: search_knowledge_base, consult_normative_document, http_request')
    print(f'   Normative Framework: {"✅ Loaded" if NORMATIVE_FRAMEWORK else "❌ Not loaded"}')
    print(f'   Enhancements:')
    print(f'     - ✅ Metadata filtering for KB retrieval')
    print(f'     - ✅ Conversation management (sliding window)')
    print(f'     - ✅ Token limit handling (auto-truncation)')
    print(f'   Configuration:')
    print(f'     - Window size: {CONVERSATION_WINDOW_SIZE} messages')
    print(f'     - Session TTL: {SESSION_TTL_MINUTES} minutes')
    print(f'     - Max response: {MAX_RESPONSE_CHARS} chars\n')

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=PORT,
        log_level='info'
    )
