"""
Ingestion Failure Handler Lambda

Captures Bedrock Knowledge Base ingestion job completion events.
Identifies failed documents that are OCR-recoverable (images, PDFs).
Invokes OCR Lambda to process them and retry ingestion.
"""

import json
import os
import re
import boto3
from typing import List, Dict, Any

# AWS clients
bedrock_agent = boto3.client('bedrock-agent')
lambda_client = boto3.client('lambda')

# Environment variables
KNOWLEDGE_BASE_ID = os.environ['KNOWLEDGE_BASE_ID']
DATA_SOURCE_ID = os.environ['DATA_SOURCE_ID']
OCR_LAMBDA_ARN = os.environ['OCR_LAMBDA_ARN']
DOCS_BUCKET = os.environ['DOCS_BUCKET']


def handler(event, context):
    """
    Main handler for ingestion job completion events

    Event format (EventBridge):
    {
      "source": "aws.bedrock",
      "detail-type": "Bedrock Knowledge Base Ingestion Job State Change",
      "detail": {
        "knowledgeBaseId": "BLJTRDGQI0",
        "dataSourceId": "B1OGNN9EMU",
        "ingestionJobId": "ABCDEF123",
        "status": "COMPLETE" | "FAILED"
      }
    }
    """
    print(f'Received event: {json.dumps(event)}')

    try:
        # Extract event details
        detail = event.get('detail', {})
        ingestion_job_id = detail.get('ingestionJobId')
        status = detail.get('status')

        print(f'Ingestion job {ingestion_job_id} status: {status}')

        # Only process COMPLETE jobs (they may have partial failures)
        # FAILED jobs mean the entire ingestion failed (not file-level failures)
        if status not in ['COMPLETE', 'FAILED']:
            print(f'Skipping job with status: {status}')
            return {
                'statusCode': 200,
                'body': json.dumps({'message': f'Skipped status: {status}'})
            }

        # Get ingestion job details to check for failures
        job_details = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            ingestionJobId=ingestion_job_id
        )

        print(f'Job details: {json.dumps(job_details, default=str)}')

        # Extract failure reasons
        failure_reasons = job_details.get('ingestionJob', {}).get('failureReasons', [])

        if not failure_reasons:
            print(f'✅ No failures found in job {ingestion_job_id}')
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No failures to process'})
            }

        print(f'⚠️  Found {len(failure_reasons)} failure reasons')

        # Parse failure reasons to extract S3 URIs
        failed_documents = parse_failure_reasons(failure_reasons)

        if not failed_documents:
            print('No OCR-recoverable documents found')
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No OCR-recoverable failures'})
            }

        print(f'🔍 Found {len(failed_documents)} OCR-recoverable documents')

        # Invoke OCR Lambda for each failed document
        results = []
        for doc in failed_documents:
            result = invoke_ocr_lambda(doc)
            results.append(result)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(results)} failed documents',
                'results': results
            })
        }

    except Exception as e:
        print(f'❌ Error processing ingestion failure: {str(e)}')
        raise


def parse_failure_reasons(failure_reasons: List[str]) -> List[Dict[str, str]]:
    """
    Parse failure reasons to extract S3 URIs of failed documents

    Failure reasons come as JSON strings containing arrays, e.g.:
    ["Encountered error: Ignored 1 files... [Files: s3://bucket/path/file.pdf]..."]

    Returns:
        List of dicts with bucket, key, and reason
    """
    failed_docs = []

    # S3 URI pattern - match until ] to capture full path with spaces
    s3_uri_pattern = r's3://([^/]+)/([^\]]+)(?:\])'

    for reason_str in failure_reasons:
        print(f'Parsing failure reason: {reason_str}')

        # Parse JSON string to get array of reasons
        try:
            reasons_array = json.loads(reason_str)
            if not isinstance(reasons_array, list):
                reasons_array = [reason_str]
        except json.JSONDecodeError:
            # Not JSON, treat as single reason
            reasons_array = [reason_str]

        for reason in reasons_array:
            print(f'  Processing: {reason[:100]}...')

            # Check if this is an OCR-recoverable error
            if not is_ocr_recoverable(reason):
                print(f'    ❌ Not OCR-recoverable, skipping')
                continue

            # Extract S3 URI
            match = re.search(s3_uri_pattern, reason)
            if match:
                bucket = match.group(1)
                key = match.group(2).strip()

                # Verify file extension is OCR-processable
                file_ext = key.lower().split('.')[-1]
                if file_ext not in ['pdf', 'png', 'jpg', 'jpeg', 'tiff']:
                    print(f'    ❌ Extension "{file_ext}" not OCR-processable, skipping')
                    continue

                failed_docs.append({
                    'bucket': bucket,
                    'key': key,
                    'reason': reason
                })

                print(f'    ✅ Added to OCR queue: s3://{bucket}/{key}')
            else:
                print(f'    ⚠️  Could not extract S3 URI from: {reason[:100]}...')

    return failed_docs


def is_ocr_recoverable(failure_reason: str) -> bool:
    """
    Check if a failure reason indicates an OCR-recoverable error

    OCR-recoverable errors:
    - "Failed to extract text" - scanned images/PDFs without text
    - "Content is not extractable" - locked/encrypted PDFs
    - "No text content found" - images without text layer

    NOT OCR-recoverable:
    - Size limit errors (need to split document first)
    - Permission errors (need to fix access)
    - Format errors (corrupt files)
    """
    ocr_recoverable_keywords = [
        'failed to extract text',
        'content is not extractable',
        'no text content found',
        'text extraction failed',
        'unable to parse',
        'file format was not supported',  # Images (PNG, JPG, etc.) not supported by KB but processable with OCR
    ]

    reason_lower = failure_reason.lower()

    for keyword in ocr_recoverable_keywords:
        if keyword in reason_lower:
            return True

    return False


def invoke_ocr_lambda(document: Dict[str, str]) -> Dict[str, Any]:
    """
    Invoke OCR Lambda to process a failed document

    Args:
        document: Dict with 'bucket', 'key', 'reason'

    Returns:
        Dict with invocation result
    """
    bucket = document['bucket']
    key = document['key']

    print(f'🚀 Invoking OCR Lambda for s3://{bucket}/{key}')

    try:
        # Build event payload for OCR Lambda
        # Format matches S3 EventBridge notification structure
        payload = {
            'source': 'ingestion-failure-handler',
            'detail': {
                'bucket': {'name': bucket},
                'object': {'key': key}
            }
        }

        # Invoke OCR Lambda asynchronously
        response = lambda_client.invoke(
            FunctionName=OCR_LAMBDA_ARN,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(payload)
        )

        print(f'  ✅ OCR Lambda invoked, status: {response["StatusCode"]}')

        return {
            'document': f's3://{bucket}/{key}',
            'status': 'invoked',
            'statusCode': response['StatusCode']
        }

    except Exception as e:
        print(f'  ❌ Error invoking OCR Lambda: {str(e)}')
        return {
            'document': f's3://{bucket}/{key}',
            'status': 'error',
            'error': str(e)
        }
