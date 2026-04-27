#!/usr/bin/env python3
"""
E2E Tests for Document Ingestion Pipeline
Tests S3 upload, OCR processing, and Knowledge Base sync
"""
import os
import boto3
import pytest
import time
from typing import Optional


# Configuration
AWS_PROFILE = os.getenv("AWS_PROFILE", "default")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DOCS_BUCKET = os.getenv("DOCS_BUCKET", "processapp-docs-v2-dev-708819485463")
KMS_KEY_ID = os.getenv("KMS_KEY_ID", "e6a714f6-70a7-47bf-a9ee-55d871d33cc6")
KB_ID = os.getenv("KB_ID", "R80HXGRLHO")


@pytest.fixture(scope="module")
def aws_clients():
    """Initialize AWS clients"""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return {
        's3': session.client('s3'),
        'bedrock_agent': session.client('bedrock-agent')
    }


def test_s3_bucket_accessible(aws_clients):
    """Test that S3 bucket exists and is accessible"""
    s3 = aws_clients['s3']

    try:
        response = s3.head_bucket(Bucket=DOCS_BUCKET)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    except Exception as e:
        pytest.fail(f"S3 bucket not accessible: {e}")


def test_upload_text_document(aws_clients):
    """Test uploading a text document to S3"""
    s3 = aws_clients['s3']

    # Test document content
    document_content = """
    ProcessApp E2E Test Document

    This is a test document for the E2E test suite.
    It contains information about the ProcessApp RAG system.

    Features:
    - Knowledge Base integration
    - Agent Core Runtime with Strand SDK
    - WebSocket streaming
    - Short-term memory (7 days)
    - Multi-tool support
    """

    key = "documents/test_e2e_upload.txt"

    try:
        # Upload document
        s3.put_object(
            Bucket=DOCS_BUCKET,
            Key=key,
            Body=document_content.encode('utf-8'),
            ContentType='text/plain',
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KMS_KEY_ID,
            Metadata={
                'test': 'e2e',
                'source': 'pytest'
            }
        )

        # Verify upload
        response = s3.head_object(Bucket=DOCS_BUCKET, Key=key)
        assert response['ContentLength'] > 0
        assert response['ServerSideEncryption'] == 'aws:kms'

    finally:
        # Cleanup
        try:
            s3.delete_object(Bucket=DOCS_BUCKET, Key=key)
        except:
            pass


def test_list_knowledge_base_data_sources(aws_clients):
    """Test listing Knowledge Base data sources"""
    bedrock_agent = aws_clients['bedrock_agent']

    try:
        response = bedrock_agent.list_data_sources(
            knowledgeBaseId=KB_ID
        )

        assert 'dataSourceSummaries' in response
        assert len(response['dataSourceSummaries']) > 0

        # Get first data source
        data_source = response['dataSourceSummaries'][0]
        assert 'dataSourceId' in data_source
        assert 'status' in data_source

    except Exception as e:
        pytest.fail(f"Failed to list data sources: {e}")


def test_knowledge_base_ingestion_job_status(aws_clients):
    """Test checking Knowledge Base ingestion job status"""
    bedrock_agent = aws_clients['bedrock_agent']

    try:
        # Get data source ID
        data_sources = bedrock_agent.list_data_sources(knowledgeBaseId=KB_ID)
        data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']

        # List recent ingestion jobs
        response = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id,
            maxResults=5
        )

        assert 'ingestionJobSummaries' in response

        if len(response['ingestionJobSummaries']) > 0:
            latest_job = response['ingestionJobSummaries'][0]
            assert 'status' in latest_job
            assert latest_job['status'] in [
                'STARTING', 'IN_PROGRESS', 'COMPLETE', 'FAILED', 'STOPPING', 'STOPPED'
            ]

    except Exception as e:
        pytest.fail(f"Failed to check ingestion job status: {e}")


def test_start_ingestion_job(aws_clients):
    """Test starting a Knowledge Base ingestion job"""
    bedrock_agent = aws_clients['bedrock_agent']

    # Skip this test in CI/CD (only run manually)
    if os.getenv("CI"):
        pytest.skip("Skipping ingestion job start in CI/CD")

    try:
        # Get data source ID
        data_sources = bedrock_agent.list_data_sources(knowledgeBaseId=KB_ID)
        data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']

        # Start ingestion job
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id,
            description="E2E test ingestion job"
        )

        assert 'ingestionJob' in response
        assert response['ingestionJob']['status'] in ['STARTING', 'IN_PROGRESS']

        job_id = response['ingestionJob']['ingestionJobId']

        # Wait a bit for job to start
        time.sleep(5)

        # Check job status
        job_response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=data_source_id,
            ingestionJobId=job_id
        )

        assert 'ingestionJob' in job_response
        assert job_response['ingestionJob']['status'] in [
            'STARTING', 'IN_PROGRESS', 'COMPLETE'
        ]

    except Exception as e:
        pytest.fail(f"Failed to start ingestion job: {e}")


def test_document_count_in_s3(aws_clients):
    """Test counting documents in S3 bucket"""
    s3 = aws_clients['s3']

    try:
        response = s3.list_objects_v2(
            Bucket=DOCS_BUCKET,
            Prefix='documents/'
        )

        if 'Contents' in response:
            document_count = len(response['Contents'])
            print(f"\nTotal documents in S3: {document_count}")
            assert document_count > 0, "Expected at least one document in S3"
        else:
            pytest.fail("No documents found in S3")

    except Exception as e:
        pytest.fail(f"Failed to count documents: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
