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

    def to_dict(self) -> Dict[str, Any]:
        """Convert RequestMetadata to JSON-serializable dict"""
        return {
            'tenant_id': self.tenant_id,
            'project_id': self.project_id,
            'task_id': self.task_id,
            'subtask_id': self.subtask_id,
            'user_id': self.user_id,
            'user_roles': self.user_roles,
            'users': self.users,
            'team_ids': self.team_ids,
            'knowledge_type': self.knowledge_type,
            'attachment_id': self.attachment_id,
            'attachment_type': self.attachment_type,
            'org_document_type': self.org_document_type,
            'org_document_sub_type': self.org_document_sub_type,
            'partition_type': self.partition_type,
            'task_names': self.task_names,
            'user_access_chain': self.user_access_chain,
            'additional_filters': self.additional_filters
        }


class KBFilterBuilder:
    """
    Builds AWS Bedrock Knowledge Base retrieval filters from metadata.

    Supports multi-tenant isolation via metadata filtering.
    Filter structure follows AWS Bedrock API format.
    """

    @staticmethod
    def generate_partition_key(tenant_id: str, project_id: str = None, task_id: str = None) -> Optional[str]:
        """
        Generate partition_key from tenant_id, project_id, and optional task_id.

        Format:
        - Project-level: t{tenant}_p{project}
        - Task-level: t{tenant}_p{project}_t{task}

        Examples:
        - generate_partition_key("1001", "165") -> "t1001_p165"
        - generate_partition_key("1001", "165", "174") -> "t1001_p165_t174"
        """
        if not tenant_id or not project_id:
            return None

        partition_key = f"t{tenant_id}_p{project_id}"
        if task_id:
            partition_key += f"_t{task_id}"

        return partition_key

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
            partition_key = KBFilterBuilder.generate_partition_key(
                metadata.tenant_id,
                metadata.project_id,
                metadata.task_id
            )
            if partition_key:
                conditions.append({
                    'equals': {
                        'key': 'partition_key',
                        'value': partition_key
                    }
                })
                print(f'[KB Filter] ✅ partition_key (task only): {partition_key}')

        elif metadata.project_id:
            # STRICT: Only project-level docs (exclude tasks)
            partition_key_project = KBFilterBuilder.generate_partition_key(
                metadata.tenant_id,
                metadata.project_id
            )
            if partition_key_project:
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

        # 3. Subtask filter (if present) - OPTIONAL
        if metadata.subtask_id:
            conditions.append({
                'equals': {
                    'key': 'subtask_id',
                    'value': str(metadata.subtask_id)
                }
            })
            print(f'[KB Filter] ✅ subtask_id: {metadata.subtask_id}')

        # IMPORTANT: Only the above filters are used for KB filtering
        # The following fields are extracted but NOT used in KB filters:
        # - knowledge_type, partition_type (not in S3 metadata)
        # - user_roles, users, team_ids (access control, not storage metadata)
        # - attachment_type, org_document_type (document classification, not in KB metadata)
        # - userAgent, referrer, timestamp (frontend metadata, not in KB)

        # NOTE: We do NOT add additional_filters to KB filter
        # Fields like userAgent, referrer, timestamp are NOT stored in S3 metadata
        # Only the fields above (tenant_id, project_id, partition_key, etc.) are valid KB filters

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

        Priority: Headers > Body.metadata object > Body root level

        Expected headers (case-insensitive):
        - X-Tenant-Id
        - X-User-Id
        - X-User-Roles (comma-separated)
        - X-Project-Id
        - X-Task-Id
        - X-Subtask-Id
        - X-Knowledge-Type
        - X-Partition-Type

        Expected body structure (NEW):
        {
          "inputText": "...",
          "sessionId": "...",
          "metadata": {
            "tenant_id": "1",
            "project_id": "165",
            "task_id": "174",
            ...
          }
        }
        """
        # Normalize headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Extract metadata object from body (NEW: preferred location)
        metadata_obj = body.get('metadata', {})

        # DEBUG: Log what we received
        print(f'[Metadata Extract] Body keys: {list(body.keys())}')
        print(f'[Metadata Extract] Metadata object keys: {list(metadata_obj.keys())}')
        print(f'[Metadata Extract] Metadata object content: {metadata_obj}')

        # Extract from headers (primary source)
        tenant_id = headers_lower.get('x-tenant-id')
        user_id = headers_lower.get('x-user-id')
        user_roles_str = headers_lower.get('x-user-roles')
        project_id = headers_lower.get('x-project-id')
        task_id = headers_lower.get('x-task-id')
        subtask_id = headers_lower.get('x-subtask-id')
        knowledge_type = headers_lower.get('x-knowledge-type')
        partition_type = headers_lower.get('x-partition-type')

        # Fallback to body.metadata object, then body root level (priority order)
        if not tenant_id:
            tenant_id = metadata_obj.get('tenant_id') or metadata_obj.get('tenantId') or body.get('tenant_id') or body.get('tenantId')
            print(f'[Metadata Extract] tenant_id extracted: {tenant_id}')
        if not user_id:
            user_id = metadata_obj.get('user_id') or metadata_obj.get('userId') or body.get('user_id') or body.get('userId')
        if not user_roles_str:
            user_roles_str = metadata_obj.get('user_roles') or metadata_obj.get('userRoles') or body.get('user_roles') or body.get('userRoles') or body.get('roles')
        if not project_id:
            project_id = metadata_obj.get('project_id') or metadata_obj.get('projectId') or body.get('project_id') or body.get('projectId')
            print(f'[Metadata Extract] project_id extracted: {project_id}')
        if not task_id:
            task_id = metadata_obj.get('task_id') or metadata_obj.get('taskId') or body.get('task_id') or body.get('taskId')
            print(f'[Metadata Extract] task_id extracted: {task_id}')
        if not subtask_id:
            subtask_id = metadata_obj.get('subtask_id') or metadata_obj.get('subtaskId') or body.get('subtask_id') or body.get('subtaskId')
        if not knowledge_type:
            knowledge_type = metadata_obj.get('knowledge_type') or metadata_obj.get('knowledgeType') or body.get('knowledge_type') or body.get('knowledgeType')
        if not partition_type:
            partition_type = metadata_obj.get('partition_type') or metadata_obj.get('partitionType') or body.get('partition_type') or body.get('partitionType')

        # Extract additional fields from metadata object or body (priority: metadata_obj > body)
        attachment_id = metadata_obj.get('attachment_id') or metadata_obj.get('attachmentId') or body.get('attachment_id') or body.get('attachmentId')
        attachment_type = metadata_obj.get('attachment_type') or metadata_obj.get('attachmentType') or body.get('attachment_type') or body.get('attachmentType')
        org_document_type = metadata_obj.get('org_document_type') or metadata_obj.get('orgDocumentType') or body.get('org_document_type') or body.get('orgDocumentType')
        org_document_sub_type = metadata_obj.get('org_document_sub_type') or metadata_obj.get('orgDocumentSubType') or body.get('org_document_sub_type') or body.get('orgDocumentSubType')

        users_data = metadata_obj.get('users') or body.get('users')
        team_ids_data = metadata_obj.get('team_ids') or metadata_obj.get('teamIds') or body.get('team_ids') or body.get('teamIds')
        task_names_data = metadata_obj.get('task_names') or metadata_obj.get('taskNames') or body.get('task_names') or body.get('taskNames')
        user_access_chain_data = metadata_obj.get('user_access_chain') or metadata_obj.get('userAccessChain') or body.get('user_access_chain') or body.get('userAccessChain')

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

        # Extract additional custom filters from metadata object
        # NOTE: All fields in metadata_obj are already extracted above,
        # but we keep this for any extra custom fields not explicitly handled
        additional_filters = {k: v for k, v in metadata_obj.items()
                            if k not in ['tenant_id', 'tenantId', 'project_id', 'projectId',
                                       'task_id', 'taskId', 'subtask_id', 'subtaskId',
                                       'user_id', 'userId', 'user_roles', 'userRoles',
                                       'knowledge_type', 'knowledgeType', 'partition_type', 'partitionType',
                                       'attachment_id', 'attachmentId', 'attachment_type', 'attachmentType',
                                       'org_document_type', 'orgDocumentType', 'org_document_sub_type', 'orgDocumentSubType',
                                       'users', 'team_ids', 'teamIds', 'task_names', 'taskNames',
                                       'user_access_chain', 'userAccessChain']}

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
