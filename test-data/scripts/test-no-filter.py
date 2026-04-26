#!/usr/bin/env python3
import requests
import json

API_URL = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query'
API_KEY = 'x5ots6txyN5Zz0bychGjraWWpY7ialv13BalOXUV'

# Make request WITHOUT tenant headers to test if any documents exist
response = requests.post(
    API_URL,
    headers={
        'X-Api-Key': API_KEY,
        'Content-Type': 'application/json'
    },
    json={'question': 'What documents do you have about Colpensiones?'},
    timeout=30
)

print(f"Status: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")
