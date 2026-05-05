#!/usr/bin/env python3
import boto3
import json
import uuid

# Initialize Bedrock Agent Runtime client
session = boto3.Session(profile_name='default')
bedrock_agent_runtime = session.client('bedrock-agent-runtime', region_name='us-east-1')

# Agent configuration
AGENT_ID = 'QWTVV3BY3G'
AGENT_ALIAS_ID = 'QZITGFMONE'

def ask_agent(question, session_id=None):
    """Ask a question to the Bedrock Agent"""
    if session_id is None:
        session_id = str(uuid.uuid4())

    print(f"\n{'='*60}")
    print(f"PREGUNTA: {question}")
    print(f"{'='*60}")

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=question
        )

        # Process the response stream
        answer = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    answer += chunk['bytes'].decode('utf-8')

        print(f"\nRESPUESTA:\n{answer}\n")
        return answer, session_id

    except Exception as e:
        print(f"Error: {e}")
        return None, session_id

if __name__ == "__main__":
    # Preguntas sobre el documento
    session_id = str(uuid.uuid4())

    # Pregunta 1: CEO y empleados
    ask_agent("¿Cuál es el nombre del CEO de Tech Solutions y cuántos empleados tiene la empresa?", session_id)

    # Pregunta 2: Producto principal
    ask_agent("¿Cuál es el nombre del producto principal, su versión actual y su precio?", session_id)

    # Pregunta 3: Ingresos
    ask_agent("¿Cuáles fueron los ingresos del Q4 2025 y cuál es la proyección para Q1 2026?", session_id)

    # Pregunta 4: Proyectos en desarrollo
    ask_agent("¿Qué proyectos están en desarrollo y cuál es el estado de cada uno?", session_id)

    # Pregunta 5: Clientes principales
    ask_agent("¿Quiénes son los 3 clientes principales y cuánto genera cada contrato anualmente?", session_id)
