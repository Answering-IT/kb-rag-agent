"""
Metadata Filter Builder
Constructs Bedrock KB filters from request metadata.
Follows AWS Bedrock retrieveFilter format from Strands tests.
"""

import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RequestMetadata:
    """Structured metadata from request"""
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    subtask_id: Optional[str] = None
    user_id: Optional[str] = None
    additional_filters: Dict[str, Any] = field(default_factory=dict)

    def has_filters(self) -> bool:
        """Check if any filters are present"""
        return bool(
            self.tenant_id or
            self.project_id or
            self.task_id or
            self.subtask_id or
            self.additional_filters
        )


class MetadataFilterBuilder:
    """
    Builds AWS Bedrock Knowledge Base retrieveFilter from metadata.

    Filter format follows Strands test examples:
    https://github.com/strands-agents/tools/blob/main/tests/test_retrieve.py#L513

    Example output:
    {
        "andAll": [
            {"equals": {"key": "tenant_id", "value": "1001"}},
            {"equals": {"key": "partition_key", "value": "t1001_p165"}}
        ]
    }
    """

    @staticmethod
    def extract_from_request(headers: Dict[str, str], body: Dict[str, Any]) -> RequestMetadata:
        """
        Extract metadata from HTTP request.

        Priority: Headers > body.metadata > body root

        Headers:
            X-Tenant-Id, X-Project-Id, X-Task-Id, X-Subtask-Id, X-User-Id

        Body:
            {
                "inputText": "...",
                "metadata": {
                    "tenant_id": "1001",
                    "project_id": "165",
                    ...
                }
            }
        """
        headers_lower = {k.lower(): v for k, v in headers.items()}
        metadata_obj = body.get('metadata', {})

        # Extract from headers (priority 1)
        tenant_id = headers_lower.get('x-tenant-id')
        project_id = headers_lower.get('x-project-id')
        task_id = headers_lower.get('x-task-id')
        subtask_id = headers_lower.get('x-subtask-id')
        user_id = headers_lower.get('x-user-id')

        # Fallback to body.metadata (priority 2), then body root (priority 3)
        if not tenant_id:
            tenant_id = metadata_obj.get('tenant_id') or metadata_obj.get('tenantId') or \
                       body.get('tenant_id') or body.get('tenantId')

        if not project_id:
            project_id = metadata_obj.get('project_id') or metadata_obj.get('projectId') or \
                        body.get('project_id') or body.get('projectId')

        if not task_id:
            task_id = metadata_obj.get('task_id') or metadata_obj.get('taskId') or \
                     body.get('task_id') or body.get('taskId')

        if not subtask_id:
            subtask_id = metadata_obj.get('subtask_id') or metadata_obj.get('subtaskId') or \
                        body.get('subtask_id') or body.get('subtaskId')

        if not user_id:
            user_id = metadata_obj.get('user_id') or metadata_obj.get('userId') or \
                     body.get('user_id') or body.get('userId')

        return RequestMetadata(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            subtask_id=subtask_id,
            user_id=user_id
        )

    @staticmethod
    def generate_partition_key(tenant_id: str, project_id: str = None, task_id: str = None) -> Optional[str]:
        """
        Generate partition_key from hierarchical IDs.

        Format:
            - Project: t{tenant}_p{project}
            - Task: t{tenant}_p{project}_t{task}

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
        Build Bedrock KB retrieveFilter from metadata.

        Returns filter in format compatible with Strands retrieve tool:
        {
            "andAll": [
                {"equals": {"key": "field1", "value": "value1"}},
                {"equals": {"key": "field2", "value": "value2"}}
            ]
        }

        Filtering hierarchy:
            1. tenant_id only -> All tenant documents
            2. tenant_id + project_id -> Project documents (partition_key = t{tenant}_p{project})
            3. tenant_id + project_id + task_id -> Task documents (partition_key = t{tenant}_p{project}_t{task})
        """
        if not metadata.has_filters():
            logger.info('[Filter] No metadata - unrestricted access')
            return None

        conditions = []

        # Required: tenant_id (but we'll use partition_key for filtering, tenant_id just for validation)
        if not metadata.tenant_id:
            logger.warning('[Filter] No tenant_id - unrestricted access')
            return None

        logger.info(f'[Filter] ✅ tenant_id: {metadata.tenant_id}')

        # Build partition_key based on hierarchy
        if metadata.task_id and metadata.project_id:
            # Strict: Task-level documents only
            partition_key = MetadataFilterBuilder.generate_partition_key(
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
                logger.info(f'[Filter] ✅ partition_key (task): {partition_key}')

        elif metadata.project_id:
            # Strict: Project-level documents only
            partition_key = MetadataFilterBuilder.generate_partition_key(
                metadata.tenant_id,
                metadata.project_id
            )
            if partition_key:
                conditions.append({
                    'equals': {
                        'key': 'partition_key',
                        'value': partition_key
                    }
                })
                logger.info(f'[Filter] ✅ project_id: {metadata.project_id}')
                logger.info(f'[Filter] ✅ partition_key (project): {partition_key}')

        else:
            # Tenant-only: ONLY tenant-level documents (partition_key = "t{tenant}")
            # This prevents seeing project/task documents
            tenant_partition_key = f"t{metadata.tenant_id}"
            conditions.append({
                'equals': {
                    'key': 'partition_key',
                    'value': tenant_partition_key
                }
            })
            logger.info(f'[Filter] ✅ partition_key (tenant-only): {tenant_partition_key}')

        # Optional: subtask_id
        if metadata.subtask_id:
            conditions.append({
                'equals': {
                    'key': 'subtask_id',
                    'value': str(metadata.subtask_id)
                }
            })
            logger.info(f'[Filter] ✅ subtask_id: {metadata.subtask_id}')

        if not conditions:
            return None

        logger.info(f'[Filter] Built filter with {len(conditions)} conditions')

        # If only one condition, return it directly (andAll requires 2+ conditions)
        if len(conditions) == 1:
            logger.info('[Filter] Single condition - returning equals filter directly')
            return conditions[0]

        # Multiple conditions: use andAll operator (Strands format)
        logger.info('[Filter] Multiple conditions - using andAll')
        return {'andAll': conditions}
