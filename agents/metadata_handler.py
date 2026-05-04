"""
Metadata filtering support for Bedrock Knowledge Base retrieval.
Extracts metadata from requests and builds AWS Bedrock filter structures.
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass


@dataclass
class RequestMetadata:
    """Structured metadata extracted from request - supports full metadata.fallback schema"""
    # Core identifiers
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    subtask_id: Optional[str] = None

    # Access control
    user_id: Optional[str] = None
    user_roles: Optional[List[str]] = None
    users: Optional[List[str]] = None
    team_ids: Optional[List[str]] = None

    # Knowledge classification
    knowledge_type: Optional[str] = None  # 'generic' or 'specific'

    # Document metadata
    attachment_id: Optional[str] = None
    attachment_type: Optional[str] = None
    org_document_type: Optional[str] = None
    org_document_sub_type: Optional[str] = None
    partition_type: Optional[str] = None  # 'PROJECT', 'TASK', 'SUBTASK', 'GENERIC'

    # Complex fields
    task_names: Optional[List[str]] = None
    user_access_chain: Optional[List[str]] = None

    # Additional custom filters
    additional_filters: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_filters is None:
            self.additional_filters = {}

        # Parse comma-separated values if provided as strings
        if isinstance(self.user_roles, str):
            self.user_roles = [r.strip() for r in self.user_roles.split(',') if r.strip()]

        if isinstance(self.users, str):
            self.users = [u.strip() for u in self.users.split(',') if u.strip()]

        if isinstance(self.team_ids, str):
            self.team_ids = [t.strip() for t in self.team_ids.split(',') if t.strip()]

        if isinstance(self.task_names, str):
            self.task_names = [t.strip() for t in self.task_names.split(',') if t.strip()]

    def has_filters(self) -> bool:
        """Check if any filters are present"""
        return bool(
            self.tenant_id or
            self.user_id or
            self.user_roles or
            self.project_id or
            self.task_id or
            self.subtask_id or
            self.knowledge_type or
            self.partition_type or
            self.users or
            self.team_ids or
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
        Build Bedrock KB filter from request metadata using partition_key for strict isolation.

        Filtering logic (strict hierarchy):
        1. tenant_id only → All docs from tenant (no partition filter)
        2. tenant_id + project_id → Only project docs (partition = t{tenant}_p{project}*)
        3. tenant_id + project_id + task_id → ONLY task docs (partition = t{tenant}_p{project}_t{task})

        partition_key format:
        - Project-level: t{tenant}_p{project}
        - Task-level: t{tenant}_p{project}_t{task}

        This ensures strict isolation without false positives.
        """
        if not metadata.has_filters():
            print('[KB Filter] No metadata provided - unrestricted access')
            return None

        conditions = []

        # 1. Required filter: tenant_id (ALWAYS required)
        if not metadata.tenant_id:
            print('[KB Filter] ⚠️  No tenant_id - unrestricted access')
            return None

        conditions.append({
            'equals': {
                'key': 'tenant_id',
                'value': str(metadata.tenant_id)
            }
        })
        print(f'[KB Filter] ✅ tenant_id: {metadata.tenant_id}')

        # 2. Build partition_key filter based on hierarchy
        if metadata.task_id and metadata.project_id:
            # STRICT: Only task-level docs
            partition_key = f"t{metadata.tenant_id}_p{metadata.project_id}_t{metadata.task_id}"
            conditions.append({
                'equals': {
                    'key': 'partition_key',
                    'value': partition_key
                }
            })
            print(f'[KB Filter] ✅ partition_key (task only): {partition_key}')

        elif metadata.project_id:
            # Project + all its tasks: Use orAll with startsWith pattern
            # Since Bedrock doesn't support startsWith, we use explicit equals for project-level
            # and rely on tenant_id + project_id matching
            partition_key_project = f"t{metadata.tenant_id}_p{metadata.project_id}"

            # Add both project_id and partition_key for double validation
            conditions.append({
                'equals': {
                    'key': 'project_id',
                    'value': str(metadata.project_id)
                }
            })
            conditions.append({
                'equals': {
                    'key': 'partition_key',
                    'value': partition_key_project
                }
            })
            print(f'[KB Filter] ✅ project_id: {metadata.project_id}')
            print(f'[KB Filter] ✅ partition_key (project only): {partition_key_project}')

        # 3. Knowledge type filter (generic vs specific)
        if metadata.knowledge_type:
            conditions.append({
                'equals': {
                    'key': 'knowledge_type',
                    'value': metadata.knowledge_type
                }
            })
            print(f'[KB Filter] ✅ knowledge_type: {metadata.knowledge_type}')

        # 4. Subtask filter (if present)
        if metadata.subtask_id:
            conditions.append({
                'equals': {
                    'key': 'subtask_id',
                    'value': str(metadata.subtask_id)
                }
            })
            print(f'[KB Filter] ✅ subtask_id: {metadata.subtask_id}')

        # 4. Partition type filter (PROJECT, TASK, SUBTASK, GENERIC)
        if metadata.partition_type:
            conditions.append({
                'equals': {
                    'key': 'partition_type',
                    'value': metadata.partition_type
                }
            })
            print(f'[KB Filter] Added partition_type: {metadata.partition_type}')

        # 5. User roles filter (multi-value with OR logic)
        if metadata.user_roles:
            # User with ANY of these roles can access
            role_conditions = [
                {'equals': {'key': 'user_roles', 'value': role}}
                for role in metadata.user_roles
            ]

            # Add wildcard "*" to allow documents accessible to all roles
            role_conditions.append({
                'equals': {'key': 'user_roles', 'value': '*'}
            })

            conditions.append({
                'orAll': role_conditions
            })
            print(f'[KB Filter] Added user_roles: {metadata.user_roles}')

        # 6. Users filter (specific user access with OR logic)
        if metadata.users:
            user_conditions = [
                {'equals': {'key': 'users', 'value': user}}
                for user in metadata.users
            ]

            # Add wildcard "*" to allow documents accessible to all users
            user_conditions.append({
                'equals': {'key': 'users', 'value': '*'}
            })

            conditions.append({
                'orAll': user_conditions
            })
            print(f'[KB Filter] Added users: {metadata.users}')

        # 7. Team IDs filter (multi-value with OR logic)
        if metadata.team_ids:
            team_conditions = [
                {'equals': {'key': 'team_ids', 'value': team_id}}
                for team_id in metadata.team_ids
            ]

            conditions.append({
                'orAll': team_conditions
            })
            print(f'[KB Filter] Added team_ids: {metadata.team_ids}')

        # 8. Document type filters
        if metadata.attachment_type:
            conditions.append({
                'equals': {
                    'key': 'attachment_type',
                    'value': metadata.attachment_type
                }
            })
            print(f'[KB Filter] Added attachment_type: {metadata.attachment_type}')

        if metadata.org_document_type:
            conditions.append({
                'equals': {
                    'key': 'org_document_type',
                    'value': metadata.org_document_type
                }
            })
            print(f'[KB Filter] Added org_document_type: {metadata.org_document_type}')

        # 9. Additional custom filters
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
        Supports full metadata.fallback schema.

        Priority: Headers > Body

        Expected headers (case-insensitive):
        - X-Tenant-Id
        - X-User-Id
        - X-User-Roles (comma-separated)
        - X-Project-Id
        - X-Task-Id
        - X-Subtask-Id
        - X-Knowledge-Type
        - X-Partition-Type
        """
        # Normalize headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Extract from headers (primary source)
        tenant_id = headers_lower.get('x-tenant-id')
        user_id = headers_lower.get('x-user-id')
        user_roles_str = headers_lower.get('x-user-roles')
        project_id = headers_lower.get('x-project-id')
        task_id = headers_lower.get('x-task-id')
        subtask_id = headers_lower.get('x-subtask-id')
        knowledge_type = headers_lower.get('x-knowledge-type')
        partition_type = headers_lower.get('x-partition-type')

        # Fallback to body if headers not present (snake_case preferred for AWS Bedrock)
        if not tenant_id:
            tenant_id = body.get('tenant_id') or body.get('tenantId')
        if not user_id:
            user_id = body.get('user_id') or body.get('userId')
        if not user_roles_str:
            user_roles_str = body.get('user_roles') or body.get('userRoles') or body.get('roles')
        if not project_id:
            project_id = body.get('project_id') or body.get('projectId')
        if not task_id:
            task_id = body.get('task_id') or body.get('taskId')
        if not subtask_id:
            subtask_id = body.get('subtask_id') or body.get('subtaskId')
        if not knowledge_type:
            knowledge_type = body.get('knowledge_type') or body.get('knowledgeType')
        if not partition_type:
            partition_type = body.get('partition_type') or body.get('partitionType')

        # Extract additional fields from body
        attachment_id = body.get('attachment_id') or body.get('attachmentId')
        attachment_type = body.get('attachment_type') or body.get('attachmentType')
        org_document_type = body.get('org_document_type') or body.get('orgDocumentType')
        org_document_sub_type = body.get('org_document_sub_type') or body.get('orgDocumentSubType')

        users_data = body.get('users')
        team_ids_data = body.get('team_ids') or body.get('teamIds')
        task_names_data = body.get('task_names') or body.get('taskNames')
        user_access_chain_data = body.get('user_access_chain') or body.get('userAccessChain')

        # Parse comma-separated or list values
        user_roles = None
        if user_roles_str:
            if isinstance(user_roles_str, str):
                user_roles = [r.strip() for r in user_roles_str.split(',') if r.strip()]
            elif isinstance(user_roles_str, list):
                user_roles = user_roles_str

        users = None
        if users_data:
            if isinstance(users_data, str):
                users = [u.strip() for u in users_data.split(',') if u.strip()]
            elif isinstance(users_data, list):
                users = users_data

        team_ids = None
        if team_ids_data:
            if isinstance(team_ids_data, str):
                team_ids = [t.strip() for t in team_ids_data.split(',') if t.strip()]
            elif isinstance(team_ids_data, list):
                team_ids = team_ids_data

        task_names = None
        if task_names_data:
            if isinstance(task_names_data, str):
                task_names = [t.strip() for t in task_names_data.split(',') if t.strip()]
            elif isinstance(task_names_data, list):
                task_names = task_names_data

        user_access_chain = None
        if user_access_chain_data:
            if isinstance(user_access_chain_data, str):
                user_access_chain = [u.strip() for u in user_access_chain_data.split(',') if u.strip()]
            elif isinstance(user_access_chain_data, list):
                user_access_chain = user_access_chain_data

        # Extract additional custom filters from body
        additional_filters = body.get('metadata', {})

        metadata = RequestMetadata(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            subtask_id=subtask_id,
            user_id=user_id,
            user_roles=user_roles,
            users=users,
            team_ids=team_ids,
            knowledge_type=knowledge_type,
            attachment_id=attachment_id,
            attachment_type=attachment_type,
            org_document_type=org_document_type,
            org_document_sub_type=org_document_sub_type,
            partition_type=partition_type,
            task_names=task_names,
            user_access_chain=user_access_chain,
            additional_filters=additional_filters
        )

        print(f'[Metadata] Extracted: tenant={tenant_id}, project={project_id}, task={task_id}, '
              f'knowledge_type={knowledge_type}, partition={partition_type}, roles={user_roles}')

        return metadata
