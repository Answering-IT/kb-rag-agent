# 🚀 Quick Start - ProcessApp RAG

Inicio rápido en 2 pasos.

---

## 1️⃣ Configurar AWS

```bash
export AWS_PROFILE=default
aws sts get-caller-identity
```

Debe mostrar:
- **Account:** `708819485463`
- **Region:** `us-east-1`

---

## 2️⃣ Probar el Agente

```bash
python3 scripts/test-agent.py
```

**¡Eso es todo!** 🎉

---

## 📝 Ejemplo Manual

```python
import boto3
import uuid

session = boto3.Session(profile_name='default')
bedrock = session.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock.invoke_agent(
    agentId='QWTVV3BY3G',
    agentAliasId='QZITGFMONE',
    sessionId=str(uuid.uuid4()),
    inputText='What documents do you have?'
)

answer = ""
for event in response['completion']:
    if 'chunk' in event:
        answer += event['chunk']['bytes'].decode('utf-8')

print(answer)
```

---

## 📚 Siguiente Paso

Para desarrollo avanzado y despliegue: **[CLAUDE.md](CLAUDE.md)**

---

**Cuenta:** 708819485463 | **Perfil:** default | **Región:** us-east-1
