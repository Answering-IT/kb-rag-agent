"""
Unit tests for metadata filter
Tests the TenantContext class and KB filter builder
"""

import unittest
import sys
import os

# Add parent directory to path to import metadata_filter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambdas/api-handler'))

from metadata_filter import TenantContext


class TestTenantContext(unittest.TestCase):
    """Test cases for TenantContext class"""

    def test_build_kb_filter_tenant_only(self):
        """Test filter with only tenantId"""
        context = TenantContext(tenant_id='1')
        kb_filter = context.build_kb_filter()

        self.assertIn('andAll', kb_filter)
        self.assertEqual(len(kb_filter['andAll']), 1)
        self.assertEqual(
            kb_filter['andAll'][0],
            {'equals': {'key': 'tenantId', 'value': '1'}}
        )

    def test_build_kb_filter_with_roles(self):
        """Test filter includes role options"""
        context = TenantContext(
            tenant_id='1',
            roles=['viewer', 'editor']
        )
        kb_filter = context.build_kb_filter()

        self.assertEqual(len(kb_filter['andAll']), 2)

        # Check tenant filter
        self.assertEqual(
            kb_filter['andAll'][0],
            {'equals': {'key': 'tenantId', 'value': '1'}}
        )

        # Check role filter (should include user roles + wildcard)
        role_filter = kb_filter['andAll'][1]
        self.assertIn('orAll', role_filter)
        self.assertEqual(len(role_filter['orAll']), 3)  # 2 roles + wildcard

        role_conditions = role_filter['orAll']
        self.assertIn({'equals': {'key': 'roles', 'value': 'viewer'}}, role_conditions)
        self.assertIn({'equals': {'key': 'roles', 'value': 'editor'}}, role_conditions)
        self.assertIn({'equals': {'key': 'roles', 'value': '*'}}, role_conditions)

    def test_build_kb_filter_with_project(self):
        """Test filter includes projectId"""
        context = TenantContext(
            tenant_id='1',
            project_id='100'
        )
        kb_filter = context.build_kb_filter()

        self.assertEqual(len(kb_filter['andAll']), 2)

        # Check project filter
        project_filter = kb_filter['andAll'][1]
        self.assertIn('orAll', project_filter)
        self.assertEqual(len(project_filter['orAll']), 2)  # project ID + wildcard

        project_conditions = project_filter['orAll']
        self.assertIn({'equals': {'key': 'projectId', 'value': '100'}}, project_conditions)
        self.assertIn({'equals': {'key': 'projectId', 'value': '*'}}, project_conditions)

    def test_build_kb_filter_complete(self):
        """Test filter with all metadata dimensions"""
        context = TenantContext(
            tenant_id='1',
            user_id='user123',
            roles=['supervisor', 'asesor'],
            project_id='100',
            users=['user123', 'user456']
        )
        kb_filter = context.build_kb_filter()

        # Should have 4 filters: tenant, roles, project, users
        self.assertEqual(len(kb_filter['andAll']), 4)

        # Verify structure
        self.assertIn('andAll', kb_filter)
        self.assertEqual(kb_filter['andAll'][0]['equals']['key'], 'tenantId')
        self.assertEqual(kb_filter['andAll'][1]['orAll'][0]['equals']['key'], 'roles')
        self.assertEqual(kb_filter['andAll'][2]['orAll'][0]['equals']['key'], 'projectId')
        self.assertEqual(kb_filter['andAll'][3]['orAll'][0]['equals']['key'], 'users')

    def test_wildcard_handling(self):
        """Test wildcard ['*'] included in orAll conditions"""
        context = TenantContext(
            tenant_id='1',
            roles=['viewer'],
            project_id='100'
        )
        kb_filter = context.build_kb_filter()

        # Check roles wildcard
        role_filter = kb_filter['andAll'][1]['orAll']
        self.assertIn({'equals': {'key': 'roles', 'value': '*'}}, role_filter)

        # Check project wildcard
        project_filter = kb_filter['andAll'][2]['orAll']
        self.assertIn({'equals': {'key': 'projectId', 'value': '*'}}, project_filter)

    def test_filter_json_structure(self):
        """Validate filter conforms to Bedrock KB format"""
        context = TenantContext(
            tenant_id='1',
            roles=['viewer']
        )
        kb_filter = context.build_kb_filter()

        # Must have top-level 'andAll'
        self.assertIsInstance(kb_filter, dict)
        self.assertIn('andAll', kb_filter)
        self.assertIsInstance(kb_filter['andAll'], list)

        # Each condition must have correct structure
        for condition in kb_filter['andAll']:
            self.assertIsInstance(condition, dict)
            # Must have either 'equals' or 'orAll'
            self.assertTrue('equals' in condition or 'orAll' in condition)

            if 'equals' in condition:
                # Check equals structure
                self.assertIn('key', condition['equals'])
                self.assertIn('value', condition['equals'])

            if 'orAll' in condition:
                # Check orAll structure
                self.assertIsInstance(condition['orAll'], list)
                for or_condition in condition['orAll']:
                    self.assertIn('equals', or_condition)
                    self.assertIn('key', or_condition['equals'])
                    self.assertIn('value', or_condition['equals'])

    def test_missing_tenant_id_raises_error(self):
        """Test that missing tenant_id raises ValueError"""
        context = TenantContext(tenant_id=None)

        with self.assertRaises(ValueError) as cm:
            context.build_kb_filter()

        self.assertIn('tenant_id is required', str(cm.exception))

    def test_from_headers(self):
        """Test creating TenantContext from headers and body"""
        headers = {
            'x-tenant-id': '1',
            'x-user-id': 'user123',
            'x-user-roles': '["viewer", "editor"]'
        }
        body = {
            'projectId': '100',
            'allowedUsers': ['user123']
        }

        context = TenantContext.from_headers(headers, body)

        self.assertEqual(context.tenant_id, '1')
        self.assertEqual(context.user_id, 'user123')
        self.assertEqual(context.roles, ['viewer', 'editor'])
        self.assertEqual(context.project_id, '100')
        self.assertEqual(context.users, ['user123'])

    def test_from_headers_case_insensitive(self):
        """Test that header parsing is case-insensitive"""
        headers = {
            'X-Tenant-Id': '1',  # Different case
            'x-user-id': 'user123',
        }
        body = {}

        context = TenantContext.from_headers(headers, body)

        # Should still extract tenant_id (API Gateway lowercases headers)
        # Note: In reality, API Gateway lowercases all headers
        # so this test assumes the from_headers method handles that

    def test_to_dict(self):
        """Test converting context to dictionary"""
        context = TenantContext(
            tenant_id='1',
            user_id='user123',
            roles=['viewer'],
            project_id='100'
        )

        context_dict = context.to_dict()

        self.assertEqual(context_dict['tenant_id'], '1')
        self.assertEqual(context_dict['user_id'], 'user123')
        self.assertEqual(context_dict['roles'], ['viewer'])
        self.assertEqual(context_dict['project_id'], '100')

    def test_empty_roles_skips_role_filter(self):
        """Test that empty roles list doesn't add role filter"""
        context = TenantContext(tenant_id='1', roles=[])
        kb_filter = context.build_kb_filter()

        # Should only have tenant filter
        self.assertEqual(len(kb_filter['andAll']), 1)

    def test_none_project_id_skips_project_filter(self):
        """Test that None projectId doesn't add project filter"""
        context = TenantContext(tenant_id='1', project_id=None)
        kb_filter = context.build_kb_filter()

        # Should only have tenant filter
        self.assertEqual(len(kb_filter['andAll']), 1)


class TestFilterScenarios(unittest.TestCase):
    """Test realistic filtering scenarios"""

    def test_scenario_tenant_isolation(self):
        """Scenario: User from tenant 1 should only see tenant 1 docs"""
        tenant1_user = TenantContext(tenant_id='1')
        filter1 = tenant1_user.build_kb_filter()

        tenant2_user = TenantContext(tenant_id='2')
        filter2 = tenant2_user.build_kb_filter()

        # Filters should be different
        self.assertNotEqual(
            filter1['andAll'][0]['equals']['value'],
            filter2['andAll'][0]['equals']['value']
        )

    def test_scenario_role_based_access(self):
        """Scenario: Supervisor + Asesor can access supervisor-only docs"""
        context = TenantContext(
            tenant_id='1',
            roles=['9-supervisor', '10-asesor']
        )
        kb_filter = context.build_kb_filter()

        role_conditions = kb_filter['andAll'][1]['orAll']

        # Should include both roles
        self.assertIn(
            {'equals': {'key': 'roles', 'value': '9-supervisor'}},
            role_conditions
        )
        self.assertIn(
            {'equals': {'key': 'roles', 'value': '10-asesor'}},
            role_conditions
        )

    def test_scenario_project_scoped_access(self):
        """Scenario: User with project 1 can only access project 1 docs"""
        context = TenantContext(
            tenant_id='1',
            project_id='1'
        )
        kb_filter = context.build_kb_filter()

        # Should have project filter
        project_filter = kb_filter['andAll'][1]['orAll']
        self.assertIn(
            {'equals': {'key': 'projectId', 'value': '1'}},
            project_filter
        )

    def test_scenario_user_list_restriction(self):
        """Scenario: Document restricted to specific users"""
        context = TenantContext(
            tenant_id='1',
            users=['xyz', 'ijk']
        )
        kb_filter = context.build_kb_filter()

        # Should have user filter
        user_filter = kb_filter['andAll'][1]['orAll']
        self.assertIn(
            {'equals': {'key': 'users', 'value': 'xyz'}},
            user_filter
        )
        self.assertIn(
            {'equals': {'key': 'users', 'value': 'ijk'}},
            user_filter
        )


if __name__ == '__main__':
    unittest.main()
