"""
Metadata filtering support for Bedrock Knowledge Base retrieval.
Extracts metadata from requests and builds AWS Bedrock filter structures.
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass


@dataclass
class RequestMetadata:
    """Structured metadata extracted from request"""
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    user_roles: Optional[List[str]] = None
    project_id: Optional[str] = None
    additional_filters: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_filters is None:
            self.additional_filters = {}

        # Parse comma-separated roles if provided as string
        if isinstance(self.user_roles, str):
            self.user_roles = [r.strip() for r in self.user_roles.split(',') if r.strip()]

    def has_filters(self) -> bool:
        """Check if any filters are present"""
        return bool(
            self.tenant_id or
            self.user_id or
            self.user_roles or
            self.project_id or
            self.additional_filters
        )


class KBFilterBuilder:
    """
    Builds AWS Bedrock Knowledge Base retrieval filters from metadata.

    Supports multi-tenant isolation via metadata filtering.
    Filter structure follows AWS Bedrock API format.
    """

    @staticmethod
    def build_filter(metadata: RequestMetadata) -> Optional[Dict[str, Any]]:
        """
        Build Bedrock KB filter from request metadata.

        Returns None if no filters (allows unrestricted access).
        Returns filter dict if metadata present (restricts by tenant/user/project).

        Filter Format:
        {
            'andAll': [
                {'equals': {'key': 'tenant_id', 'value': 'company-123'}},
                {'equals': {'key': 'project_id', 'value': 'proj-456'}}
            ]
        }
        """
        if not metadata.has_filters():
            print('[KB Filter] No metadata provided - unrestricted access')
            return None

        conditions = []

        # Required filter: tenant_id (highest priority)
        if metadata.tenant_id:
            conditions.append({
                'equals': {
                    'key': 'tenant_id',
                    'value': metadata.tenant_id
                }
            })
            print(f'[KB Filter] Added tenant_id: {metadata.tenant_id}')

        # Optional filter: project_id
        if metadata.project_id:
            conditions.append({
                'equals': {
                    'key': 'project_id',
                    'value': metadata.project_id
                }
            })
            print(f'[KB Filter] Added project_id: {metadata.project_id}')

        # Optional filter: user_roles (multi-value with OR)
        if metadata.user_roles:
            # User with ANY of these roles can access
            role_conditions = [
                {'equals': {'key': 'allowed_roles', 'value': role}}
                for role in metadata.user_roles
            ]

            # Add wildcard "*" to allow documents accessible to all roles
            role_conditions.append({
                'equals': {'key': 'allowed_roles', 'value': '*'}
            })

            conditions.append({
                'orAll': role_conditions
            })
            print(f'[KB Filter] Added user_roles: {metadata.user_roles}')

        # Additional custom filters
        for key, value in metadata.additional_filters.items():
            conditions.append({
                'equals': {
                    'key': key,
                    'value': str(value)
                }
            })
            print(f'[KB Filter] Added custom filter: {key}={value}')

        if not conditions:
            return None

        # Combine all conditions with AND
        filter_dict = {'andAll': conditions}

        print(f'[KB Filter] Built filter with {len(conditions)} conditions')
        return filter_dict

    @staticmethod
    def extract_from_request(headers: Dict[str, str], body: Dict[str, Any]) -> RequestMetadata:
        """
        Extract metadata from HTTP request headers and body.

        Priority: Headers > Body

        Expected headers (case-insensitive):
        - X-Tenant-Id
        - X-User-Id
        - X-User-Roles (comma-separated)
        - X-Project-Id
        """
        # Normalize headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Extract from headers (primary source)
        tenant_id = headers_lower.get('x-tenant-id')
        user_id = headers_lower.get('x-user-id')
        user_roles_str = headers_lower.get('x-user-roles')
        project_id = headers_lower.get('x-project-id')

        # Fallback to body if headers not present (snake_case preferred for AWS Bedrock)
        if not tenant_id:
            tenant_id = body.get('tenant_id') or body.get('tenantId')  # snake_case first
        if not user_id:
            user_id = body.get('user_id') or body.get('userId')
        if not user_roles_str:
            user_roles_str = body.get('user_roles') or body.get('userRoles') or body.get('roles')
        if not project_id:
            project_id = body.get('project_id') or body.get('projectId')

        # Parse roles
        user_roles = None
        if user_roles_str:
            if isinstance(user_roles_str, str):
                user_roles = [r.strip() for r in user_roles_str.split(',') if r.strip()]
            elif isinstance(user_roles_str, list):
                user_roles = user_roles_str

        # Extract additional custom filters from body
        additional_filters = body.get('metadata', {})

        metadata = RequestMetadata(
            tenant_id=tenant_id,
            user_id=user_id,
            user_roles=user_roles,
            project_id=project_id,
            additional_filters=additional_filters
        )

        print(f'[Metadata] Extracted: tenant={tenant_id}, user={user_id}, roles={user_roles}, project={project_id}')

        return metadata
