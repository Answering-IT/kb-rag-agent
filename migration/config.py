"""
Migration Configuration

Configuration for migrating files from legacy bucket to new KB bucket
with proper metadata generation.
"""

# AWS Configuration
AWS_PROFILE = "ans-super"
AWS_REGION = "us-east-1"

# S3 Buckets
SOURCE_BUCKET = "dev-files-colpensiones"  # Legacy bucket
DESTINATION_BUCKET = "processapp-docs-v2-dev-708819485463"  # New KB bucket
KMS_KEY_ID = "e6a714f6-70a7-47bf-a9ee-55d871d33cc6"

# API Configuration
API_BASE_URL = "https://dev.app.colpensiones.procesapp.com"
TENANT_ID = "1"

# Migration Settings
SOURCE_PREFIX = f"organizations/{TENANT_ID}/projects/"
DESTINATION_PREFIX = f"organizations/{TENANT_ID}/"
MAX_PROJECTS = 200  # Process last 200 projects only

# Rate Limiting
API_RATE_LIMIT_DELAY = 0.5  # seconds between API calls
S3_RATE_LIMIT_DELAY = 0.1   # seconds between S3 operations

# Paths
CACHE_DIR = "migration/cache"
LOGS_DIR = "migration/logs"
OUTPUT_DIR = "migration/output"

# Partition Types
PARTITION_TYPES = {
    "PROJECT": "PROJECT",
    "TASK": "TASK",
    "SUBTASK": "SUBTASK"
}

# Attachment Types Mapping (from API to metadata)
ATTACHMENT_TYPE_MAPPING = {
    "NORMAL": "NORMAL",
    "COMMUNICATION_RECEIVED": "COMMUNICATION_RECEIVED",
    "COMMUNICATION_SENT": "COMMUNICATION_SENT",
    "DRAFT": "DRAFT",
    "FINAL": "FINAL",
    # Add more as needed
}

# File Extensions to Process
ALLOWED_EXTENSIONS = [
    '.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls',
    '.png', '.jpg', '.jpeg', '.tiff', '.md'
]

# File Extensions to IGNORE (no metadata needed)
IGNORED_EXTENSIONS = [
    '.zip'  # ZIP files will not be processed by KB
]

# Metadata Schema
FILTERABLE_FIELDS = [
    "tenant_id",
    "project_id",
    "task_id",
    "subtask_id",
    "partition_key"
]

NON_FILTERABLE_FIELDS = [
    "attachment_id",
    "file_name",
    "attachment_type",
    "project_path"
]
