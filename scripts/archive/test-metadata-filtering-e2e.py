#!/usr/bin/env python3
"""
End-to-End Test: Metadata Filtering with Knowledge Types

Tests:
1. Tenant 1001 can access their specific documents (Champions League)
2. Tenant 1003 can access their specific documents (Philosophy)
3. Both tenants can access generic knowledge (normative framework)
4. Cross-tenant isolation is maintained
"""

import boto3
import json
import sys

PROFILE = 'ans-super'
REGION = 'us-east-1'

# Initialize boto3
session = boto3.Session(profile_name=PROFILE)
bedrock_runtime = session.client('bedrock-agent-runtime', region_name=REGION)
bedrock_agent = session.client('bedrock-agent', region_name=REGION)

# Get KB ID
kb_response = bedrock_agent.list_knowledge_bases()
KB_ID = None
for kb in kb_response['knowledgeBaseSummaries']:
    if 'processapp' in kb['name'].lower():
        KB_ID = kb['knowledgeBaseId']
        break

if not KB_ID:
    print("❌ Knowledge Base not found")
    sys.exit(1)

print(f"✅ Using Knowledge Base: {KB_ID}\n")


def build_filter(tenant_id, knowledge_type=None, project_id=None):
    """Build KB filter"""
    conditions = []

    if tenant_id:
        conditions.append({
            'equals': {'key': 'tenant_id', 'value': str(tenant_id)}
        })

    if knowledge_type:
        conditions.append({
            'equals': {'key': 'knowledge_type', 'value': knowledge_type}
        })

    if project_id:
        conditions.append({
            'equals': {'key': 'project_id', 'value': str(project_id)}
        })

    if not conditions:
        return None

    return {'andAll': conditions}


def search_kb(query, kb_filter, test_name):
    """Search KB with filter"""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Filter: {json.dumps(kb_filter, indent=2)}")

    try:
        config = {'vectorSearchConfiguration': {'numberOfResults': 3}}
        if kb_filter:
            config['vectorSearchConfiguration']['filter'] = kb_filter

        response = bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration=config
        )

        results = response.get('retrievalResults', [])
        print(f"\n📊 Results: {len(results)} documents found")

        for i, result in enumerate(results, 1):
            content = result.get('content', {}).get('text', '')
            location = result.get('location', {})
            s3_location = location.get('s3Location', {})
            uri = s3_location.get('uri', 'N/A')

            print(f"\n  [{i}] Document: {uri.split('/')[-1] if '/' in uri else uri}")
            print(f"      Preview: {content[:150]}...")

        return results

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return []


# Test cases
test_cases = [
    {
        "name": "Tenant 1001 - Specific Knowledge (Champions League)",
        "query": "Real Madrid Champions League semifinal",
        "filter": build_filter(tenant_id="1001", knowledge_type="specific", project_id="5001"),
        "expected_count": ">0",
        "expected_keywords": ["real madrid", "champions", "semifinal"]
    },
    {
        "name": "Tenant 1003 - Specific Knowledge (Philosophy)",
        "query": "Plato Republic philosophy",
        "filter": build_filter(tenant_id="1003", knowledge_type="specific", project_id="6001"),
        "expected_count": ">0",
        "expected_keywords": ["plato", "republic"]
    },
    {
        "name": "Tenant 1001 - Generic Knowledge (Normative)",
        "query": "Colombian pension regulations normativa pensional",
        "filter": build_filter(tenant_id="1001", knowledge_type="generic"),
        "expected_count": ">0",
        "expected_keywords": ["normativ", "pension", "colombia"]
    },
    {
        "name": "Tenant 1003 - Generic Knowledge (Normative)",
        "query": "Colombian pension regulations normativa pensional",
        "filter": build_filter(tenant_id="1003", knowledge_type="generic"),
        "expected_count": ">0",
        "expected_keywords": ["normativ", "pension", "colombia"]
    },
    {
        "name": "Cross-tenant Isolation - Tenant 1001 trying to access Tenant 1003 docs",
        "query": "Plato Republic philosophy",
        "filter": build_filter(tenant_id="1001", knowledge_type="specific", project_id="6001"),
        "expected_count": "0",
        "expected_keywords": []
    },
    {
        "name": "Cross-tenant Isolation - Tenant 1003 trying to access Tenant 1001 docs",
        "query": "Real Madrid Champions League",
        "filter": build_filter(tenant_id="1003", knowledge_type="specific", project_id="5001"),
        "expected_count": "0",
        "expected_keywords": []
    }
]

# Run tests
print("\n" + "="*60)
print("E2E Metadata Filtering Tests")
print("="*60)

passed = 0
failed = 0

for test in test_cases:
    results = search_kb(test['query'], test['filter'], test['name'])

    # Check result count
    result_count = len(results)
    expected_count = test['expected_count']

    count_pass = False
    if expected_count == "0":
        count_pass = (result_count == 0)
    elif expected_count == ">0":
        count_pass = (result_count > 0)

    # Check keywords
    keywords_pass = True
    if test['expected_keywords']:
        all_content = " ".join([r.get('content', {}).get('text', '').lower() for r in results])
        for keyword in test['expected_keywords']:
            if keyword.lower() not in all_content:
                keywords_pass = False
                print(f"\n  ⚠️  Keyword '{keyword}' not found in results")

    # Overall result
    if count_pass and keywords_pass:
        print(f"\n  ✅ PASSED")
        passed += 1
    else:
        print(f"\n  ❌ FAILED")
        if not count_pass:
            print(f"     Expected count: {expected_count}, Got: {result_count}")
        failed += 1

# Summary
print("\n" + "="*60)
print(f"Summary: {passed}/{len(test_cases)} tests passed")
print("="*60)

if failed > 0:
    print(f"\n❌ {failed} test(s) failed")
    sys.exit(1)
else:
    print("\n✅ All tests passed!")
    sys.exit(0)
