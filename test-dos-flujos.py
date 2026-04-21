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
    print("PRUEBA DE FLUJOS DE DOCUMENTOS")
    print("="*70)

    # Preguntas sobre doc-flujo-normal.txt (StreamAnalytics Pro)
    print("\n\n### DOCUMENTO 1: StreamAnalytics Pro (Flujo Normal) ###\n")

    ask_agent("¿Cuál es el precio de StreamAnalytics Pro?")
    ask_agent("¿Cuántos eventos por segundo puede procesar StreamAnalytics Pro?")
    ask_agent("¿Quién es el cliente que paga más por StreamAnalytics Pro?")

    # Preguntas sobre doc-empresa.txt (TechFlow Solutions)
    print("\n\n### DOCUMENTO 2: TechFlow Solutions (Informe Q1) ###\n")

    ask_agent("¿Cuáles fueron los ingresos de TechFlow Solutions en Q1 2026?")
    ask_agent("¿Cuál es el nombre del CEO de TechFlow Solutions?")
    ask_agent("¿Cuántos empleados tiene TechFlow Solutions y cuántos contrataron en Q1?")
    ask_agent("¿Cuáles son los proyectos activos de TechFlow Solutions y su progreso?")

    print("\n" + "="*70)
    print("PRUEBA COMPLETADA")
    print("="*70 + "\n")
