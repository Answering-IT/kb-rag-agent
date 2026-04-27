"""
Metadata Filter Utility
Builds Bedrock Knowledge Base filters for multi-tenant access control
"""

from typing import List, Optional, Dict, Any


class TenantContext:
    """
    Represents the tenant/user context for filtering knowledge base queries

    Attributes:
        tenant_id: Organization/tenant identifier (REQUIRED)
        user_id: User identifier
        roles: List of roles the user has in this tenant
        project_id: Optional project scope
        users: Optional list of allowed users
    """

    def __init__(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        users: Optional[List[str]] = None
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.roles = roles or []
        self.project_id = project_id
        self.users = users or []

    def build_kb_filter(self) -> Dict[str, Any]:
        """
        Build Bedrock KB filter for vector search

        Filter order (priority):
        1. tenantId (REQUIRED) - must match exactly
        2. roles - user must have at least one role that doc allows (supports wildcard *)
        3. projectId - must match if specified (supports wildcard *)
        4. users - user must be in list if specified (supports wildcard *)

        Returns:
            dict: Filter object compatible with retrievalConfiguration.vectorSearchConfiguration.filter

        Example filter structure:
        {
            'andAll': [
                {'equals': {'key': 'tenantId', 'value': '1'}},
                {
                    'orAll': [
                        {'equals': {'key': 'roles', 'value': 'viewer'}},
                        {'equals': {'key': 'roles', 'value': '*'}}
                    ]
                }
            ]
        }
        """
        if not self.tenant_id:
            raise ValueError("tenant_id is required for filtering")

        filter_obj = {
            'andAll': []
        }

        # 1. Tenant must match (REQUIRED - highest priority)
        # NOTE: Using snake_case for metadata keys (tenant_id, project_id)
        filter_obj['andAll'].append({
            'equals': {'key': 'tenant_id', 'value': str(self.tenant_id)}
        })

        # 2. Roles filtering (user must have at least one role that doc allows)
        if self.roles:
            role_conditions = [
                {'equals': {'key': 'roles', 'value': role}}
                for role in self.roles
            ]
            # Add wildcard condition (documents with roles=* are accessible to all)
            role_conditions.append({'equals': {'key': 'roles', 'value': '*'}})

            filter_obj['andAll'].append({
                'orAll': role_conditions
            })

        # 3. Project filtering (if projectId specified in request)
        # NOTE: Using snake_case for metadata keys (tenant_id, project_id)
        if self.project_id:
            filter_obj['andAll'].append({
                'orAll': [
                    {'equals': {'key': 'project_id', 'value': str(self.project_id)}},
                    {'equals': {'key': 'project_id', 'value': '*'}}  # Wildcard
                ]
            })

        # 4. User list filtering (if specific users specified)
        if self.users:
            user_conditions = [
                {'equals': {'key': 'users', 'value': user}}
                for user in self.users
            ]
            # Add wildcard condition
            user_conditions.append({'equals': {'key': 'users', 'value': '*'}})

            filter_obj['andAll'].append({
                'orAll': user_conditions
            })

        return filter_obj

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging/debugging"""
        return {
            'tenant_id': self.tenant_id,
            'user_id': self.user_id,
            'roles': self.roles,
            'project_id': self.project_id,
            'users': self.users,
        }

    @classmethod
    def from_headers(cls, headers: Dict[str, str], body: Dict[str, Any]) -> 'TenantContext':
        """
        Create TenantContext from API Gateway request headers and body

        Args:
            headers: HTTP headers (lowercase keys)
            body: Request body dictionary

        Returns:
            TenantContext instance
        """
        import json

        # Extract from headers (case-insensitive)
        tenant_id = headers.get('x-tenant-id')
        user_id = headers.get('x-user-id')

        # Parse roles (JSON array in header)
        roles_str = headers.get('x-user-roles', '[]')
        try:
            roles = json.loads(roles_str) if isinstance(roles_str, str) else roles_str
        except json.JSONDecodeError:
            roles = []

        # Extract from body
        project_id = body.get('projectId')
        users = body.get('allowedUsers', [])

        return cls(
            tenant_id=tenant_id,
            user_id=user_id,
            roles=roles,
            project_id=project_id,
            users=users
        )
