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

def ask_agent(question):
    """Ask a question to the Bedrock Agent"""
    session_id = str(uuid.uuid4())

    print(f"\n{'='*70}")
    print(f"PREGUNTA: {question}")
    print(f"{'='*70}")

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
        return answer

    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("\n" + "="*70)
    print("PRUEBA DE FLUJO OCR - Reporte de Incidente DataFlow")
    print("="*70)

    # Preguntas sobre el documento procesado por OCR
    ask_agent("¿Cuál fue la fecha del incidente de seguridad en DataFlow?")
    ask_agent("¿Cuál fue la IP de origen del ataque y cuántos intentos se realizaron?")
    ask_agent("¿Cuánto tiempo estuvo el sistema fuera de línea?")
    ask_agent("¿Quién fue el líder de respuesta al incidente?")
    ask_agent("¿Cuáles fueron las mejoras implementadas después del incidente?")

    print("\n" + "="*70)
    print("PRUEBA COMPLETADA")
    print("="*70 + "\n")
