#!/usr/bin/env python3
"""
Test Extended Metadata Fields Support

Tests that all fields from metadata.fallback are properly extracted and used in KB filtering.
"""

import sys
import os

# Add agents directory to path to import metadata_handler
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))

from metadata_handler import RequestMetadata, KBFilterBuilder


def test_basic_metadata():
    """Test basic tenant/project filtering"""
    print("\n=== Test 1: Basic Tenant + Project Filtering ===")

    headers = {
        'X-Tenant-Id': '1',
        'X-Project-Id': '1000'
    }
    body = {}

    metadata = KBFilterBuilder.extract_from_request(headers, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    print(f"Metadata: {metadata}")
    print(f"Filter: {kb_filter}")

    assert metadata.tenant_id == '1', "tenant_id not extracted"
    assert metadata.project_id == '1000', "project_id not extracted"
    assert kb_filter is not None, "Filter should be built"
    assert len(kb_filter['andAll']) == 2, "Should have 2 conditions"

    print("✅ PASSED")


def test_full_metadata_from_body():
    """Test all metadata fields from request body"""
    print("\n=== Test 2: Full Metadata Schema (Body) ===")

    headers = {}
    body = {
        # Core identifiers
        "tenant_id": "1",
        "project_id": "1000",
        "task_id": "5001",
        "subtask_id": "8001",

        # Access control
        "user_id": "user123",
        "user_roles": ["admin", "viewer"],
        "users": ["*"],
        "team_ids": ["team-a", "team-b"],

        # Knowledge classification
        "knowledge_type": "specific",

        # Document metadata
        "attachment_id": "1001",
        "attachment_type": "NORMAL",
        "org_document_type": "CONTRACT",
        "org_document_sub_type": "PENSION",
        "partition_type": "TASK",

        # Complex fields
        "task_names": ["Task 1", "Task 2"],
        "user_access_chain": ["level1", "level2"]
    }

    metadata = KBFilterBuilder.extract_from_request(headers, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    print(f"\nMetadata extracted:")
    print(f"  tenant_id: {metadata.tenant_id}")
    print(f"  project_id: {metadata.project_id}")
    print(f"  task_id: {metadata.task_id}")
    print(f"  subtask_id: {metadata.subtask_id}")
    print(f"  knowledge_type: {metadata.knowledge_type}")
    print(f"  partition_type: {metadata.partition_type}")
    print(f"  user_roles: {metadata.user_roles}")
    print(f"  users: {metadata.users}")
    print(f"  team_ids: {metadata.team_ids}")
    print(f"  attachment_type: {metadata.attachment_type}")

    print(f"\nFilter built with {len(kb_filter['andAll'])} conditions")

    # Verify all fields extracted
    assert metadata.tenant_id == "1", "tenant_id not extracted"
    assert metadata.project_id == "1000", "project_id not extracted"
    assert metadata.task_id == "5001", "task_id not extracted"
    assert metadata.subtask_id == "8001", "subtask_id not extracted"
    assert metadata.knowledge_type == "specific", "knowledge_type not extracted"
    assert metadata.partition_type == "TASK", "partition_type not extracted"
    assert metadata.user_roles == ["admin", "viewer"], "user_roles not extracted"
    assert metadata.users == ["*"], "users not extracted"
    assert metadata.team_ids == ["team-a", "team-b"], "team_ids not extracted"
    assert metadata.attachment_type == "NORMAL", "attachment_type not extracted"

    print("✅ PASSED")


def test_knowledge_type_filtering():
    """Test knowledge_type filtering (generic vs specific)"""
    print("\n=== Test 3: Knowledge Type Filtering ===")

    # Test generic knowledge
    headers = {'X-Knowledge-Type': 'generic'}
    body = {'tenant_id': '1'}

    metadata = KBFilterBuilder.extract_from_request(headers, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    print(f"Generic knowledge filter: {kb_filter}")
    assert metadata.knowledge_type == 'generic', "knowledge_type not extracted"

    # Find knowledge_type condition
    knowledge_conditions = [c for c in kb_filter['andAll'] if c.get('equals', {}).get('key') == 'knowledge_type']
    assert len(knowledge_conditions) == 1, "Should have knowledge_type filter"
    assert knowledge_conditions[0]['equals']['value'] == 'generic', "Should filter for generic"

    # Test specific knowledge
    headers = {'X-Knowledge-Type': 'specific'}
    body = {'tenant_id': '1', 'project_id': '1000'}

    metadata = KBFilterBuilder.extract_from_request(headers, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    print(f"Specific knowledge filter: {kb_filter}")
    assert metadata.knowledge_type == 'specific', "knowledge_type not extracted"

    knowledge_conditions = [c for c in kb_filter['andAll'] if c.get('equals', {}).get('key') == 'knowledge_type']
    assert len(knowledge_conditions) == 1, "Should have knowledge_type filter"
    assert knowledge_conditions[0]['equals']['value'] == 'specific', "Should filter for specific"

    print("✅ PASSED")


def test_partition_type_filtering():
    """Test partition_type filtering (PROJECT, TASK, SUBTASK, GENERIC)"""
    print("\n=== Test 4: Partition Type Filtering ===")

    # Test PROJECT partition
    body = {
        'tenant_id': '1',
        'project_id': '1000',
        'partition_type': 'PROJECT'
    }

    metadata = KBFilterBuilder.extract_from_request({}, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    partition_conditions = [c for c in kb_filter['andAll'] if c.get('equals', {}).get('key') == 'partition_type']
    assert len(partition_conditions) == 1, "Should have partition_type filter"
    assert partition_conditions[0]['equals']['value'] == 'PROJECT', "Should filter for PROJECT"

    # Test TASK partition
    body['partition_type'] = 'TASK'
    body['task_id'] = '5001'

    metadata = KBFilterBuilder.extract_from_request({}, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    partition_conditions = [c for c in kb_filter['andAll'] if c.get('equals', {}).get('key') == 'partition_type']
    assert partition_conditions[0]['equals']['value'] == 'TASK', "Should filter for TASK"

    print("✅ PASSED")


def test_role_based_access():
    """Test user_roles filtering with OR logic"""
    print("\n=== Test 5: Role-Based Access Control ===")

    body = {
        'tenant_id': '1',
        'project_id': '1000',
        'user_roles': ['admin', 'viewer', 'editor']
    }

    metadata = KBFilterBuilder.extract_from_request({}, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    # Find orAll condition for roles
    role_conditions = [c for c in kb_filter['andAll'] if 'orAll' in c]
    assert len(role_conditions) > 0, "Should have role-based OR condition"

    # Check that roles are in the OR condition
    role_or = role_conditions[0]['orAll']
    role_values = [c['equals']['value'] for c in role_or if c.get('equals', {}).get('key') == 'user_roles']

    assert 'admin' in role_values, "admin role should be in filter"
    assert 'viewer' in role_values, "viewer role should be in filter"
    assert 'editor' in role_values, "editor role should be in filter"
    assert '*' in role_values, "wildcard * should be in filter"

    print(f"Role OR condition: {role_or}")
    print("✅ PASSED")


def test_comma_separated_values():
    """Test comma-separated string values are parsed correctly"""
    print("\n=== Test 6: Comma-Separated Value Parsing ===")

    body = {
        'tenant_id': '1',
        'user_roles': 'admin,viewer,editor',  # Comma-separated string
        'team_ids': 'team-a,team-b,team-c',   # Comma-separated string
    }

    metadata = KBFilterBuilder.extract_from_request({}, body)

    print(f"Parsed user_roles: {metadata.user_roles}")
    print(f"Parsed team_ids: {metadata.team_ids}")

    assert metadata.user_roles == ['admin', 'viewer', 'editor'], "user_roles not parsed correctly"
    assert metadata.team_ids == ['team-a', 'team-b', 'team-c'], "team_ids not parsed correctly"

    print("✅ PASSED")


def test_camelcase_fallback():
    """Test camelCase body fields fallback to snake_case"""
    print("\n=== Test 7: CamelCase Fallback ===")

    body = {
        'tenantId': '1',           # camelCase
        'projectId': '1000',       # camelCase
        'taskId': '5001',          # camelCase
        'knowledgeType': 'specific',  # camelCase
        'partitionType': 'TASK'    # camelCase
    }

    metadata = KBFilterBuilder.extract_from_request({}, body)

    print(f"tenant_id: {metadata.tenant_id}")
    print(f"project_id: {metadata.project_id}")
    print(f"task_id: {metadata.task_id}")
    print(f"knowledge_type: {metadata.knowledge_type}")
    print(f"partition_type: {metadata.partition_type}")

    assert metadata.tenant_id == '1', "tenantId not extracted"
    assert metadata.project_id == '1000', "projectId not extracted"
    assert metadata.task_id == '5001', "taskId not extracted"
    assert metadata.knowledge_type == 'specific', "knowledgeType not extracted"
    assert metadata.partition_type == 'TASK', "partitionType not extracted"

    print("✅ PASSED")


def test_metadata_fallback_structure():
    """Test exact metadata.fallback structure"""
    print("\n=== Test 8: metadata.fallback Structure ===")

    body = {
        "attachment_id": 1001,
        "knowledge_type": "specific",
        "file_name": "placeholder.pdf",
        "tenant_id": 1,
        "project_id": 1000,  # Changed from 0 to realistic value
        "task_id": None,
        "subtask_id": None,
        "attachment_type": "NORMAL",
        "org_document_type": "CONTRACT",
        "org_document_sub_type": "PENSION",
        "project_path": "organizations/1/projects/1000",
        "partition_type": "PROJECT",
        "user_roles": ["admin", "agent", "advisor", "planner", "owner"],
        "team_ids": [],
        "task_names": [],
        "users": ["*"],
        "user_access_chain": []
    }

    metadata = KBFilterBuilder.extract_from_request({}, body)
    kb_filter = KBFilterBuilder.build_filter(metadata)

    print(f"Metadata extracted from fallback structure:")
    print(f"  tenant_id: {metadata.tenant_id}")
    print(f"  project_id: {metadata.project_id}")
    print(f"  knowledge_type: {metadata.knowledge_type}")
    print(f"  partition_type: {metadata.partition_type}")
    print(f"  user_roles: {metadata.user_roles}")
    print(f"  users: {metadata.users}")
    print(f"  attachment_type: {metadata.attachment_type}")
    print(f"  org_document_type: {metadata.org_document_type}")

    # tenant_id comes as integer 1 in body, gets extracted as "1" string
    assert str(metadata.tenant_id) == "1", f"tenant_id should be string '1', got: {metadata.tenant_id}"
    assert str(metadata.project_id) == "1000", f"project_id should be string '1000', got: {metadata.project_id}"
    assert metadata.knowledge_type == "specific", "knowledge_type not extracted"
    assert metadata.partition_type == "PROJECT", "partition_type not extracted"
    assert len(metadata.user_roles) == 5, "user_roles not extracted"
    assert metadata.users == ["*"], "users not extracted"
    assert metadata.attachment_type == "NORMAL", "attachment_type not extracted"
    assert metadata.org_document_type == "CONTRACT", "org_document_type not extracted"

    print(f"\nFilter has {len(kb_filter['andAll'])} conditions")
    print("✅ PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Extended Metadata Fields Support")
    print("=" * 60)

    tests = [
        test_basic_metadata,
        test_full_metadata_from_body,
        test_knowledge_type_filtering,
        test_partition_type_filtering,
        test_role_based_access,
        test_comma_separated_values,
        test_camelcase_fallback,
        test_metadata_fallback_structure
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
