"""
Session Memory Module - DynamoDB conversation history
Manages conversation context and history persistence
"""

import boto3
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# DynamoDB client
dynamodb = boto3.resource('dynamodb')


class SessionMemory:
    """
    Manages conversation history in DynamoDB
    """
    
    def __init__(self, table_name: str, ttl_days: int = 90):
        """
        Initialize session memory manager
        
        Args:
            table_name: DynamoDB table name
            ttl_days: Number of days before conversation expires (default 90)
        """
        self.table = dynamodb.Table(table_name)
        self.ttl_days = ttl_days
    
    def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Retrieve last N messages from conversation
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to retrieve (default 10)
        
        Returns:
            List of message dicts with 'role' and 'content' keys
            Ordered oldest to newest
        """
        try:
            response = self.table.query(
                KeyConditionExpression='sessionId = :sid',
                ExpressionAttributeValues={':sid': session_id},
                ScanIndexForward=False,  # Get newest first
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Reverse to get oldest first (chronological order)
            items.reverse()
            
            # Format for agent context
            messages = []
            for item in items:
                messages.append({
                    'role': item.get('role', 'user'),
                    'content': item.get('content', ''),
                    'timestamp': item.get('timestamp')
                })
            
            return messages
        
        except Exception as e:
            print(f'Error retrieving conversation history: {str(e)}')
            return []
    
    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a message to conversation history
        
        Args:
            session_id: Session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            user_id: User ID (optional, for GSI queries)
            tenant_id: Tenant ID (optional, for filtering)
            metadata: Additional metadata (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(time.time() * 1000)  # Milliseconds
            
            # Calculate expiration time (90 days from now)
            expiration_time = int(
                (datetime.now() + timedelta(days=self.ttl_days)).timestamp()
            )
            
            item = {
                'sessionId': session_id,
                'timestamp': timestamp,
                'role': role,
                'content': content,
                'expirationTime': expiration_time,
            }
            
            # Add optional fields
            if user_id:
                item['userId'] = user_id
            if tenant_id:
                item['tenantId'] = tenant_id
            if metadata:
                item['metadata'] = metadata
            
            self.table.put_item(Item=item)
            
            print(f'Saved message to DynamoDB: sessionId={session_id}, role={role}')
            return True
        
        except Exception as e:
            print(f'Error saving message to DynamoDB: {str(e)}')
            return False
    
    def format_conversation_context(
        self, 
        messages: List[Dict[str, str]]
    ) -> str:
        """
        Format conversation history as text for agent prompt
        
        Args:
            messages: List of message dicts
        
        Returns:
            Formatted conversation string
        """
        if not messages:
            return ""
        
        context_lines = ["Previous conversation:"]
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'user':
                context_lines.append(f"User: {content}")
            else:
                context_lines.append(f"Assistant: {content}")
        
        return "\n".join(context_lines)
    
    def inject_context_in_prompt(
        self, 
        question: str, 
        session_id: str,
        context_limit: int = 10
    ) -> str:
        """
        Retrieve conversation history and inject into prompt
        
        Args:
            question: Current user question
            session_id: Session ID
            context_limit: Max number of previous messages to include
        
        Returns:
            Enhanced prompt with conversation context
        """
        messages = self.get_conversation_history(session_id, limit=context_limit)
        
        if not messages:
            # No prior context, return question as-is
            return question
        
        # Format context
        context = self.format_conversation_context(messages)
        
        # Inject context before current question
        enhanced_prompt = f"""{context}

Current question: {question}

Please answer the current question taking into account the previous conversation context."""
        
        return enhanced_prompt
    
    def clear_session(self, session_id: str) -> bool:
        """
        Delete all messages for a session
        
        Args:
            session_id: Session ID to clear
        
        Returns:
            True if successful
        """
        try:
            response = self.table.query(
                KeyConditionExpression='sessionId = :sid',
                ExpressionAttributeValues={':sid': session_id},
                ProjectionExpression='sessionId, #ts',
                ExpressionAttributeNames={'#ts': 'timestamp'}
            )
            
            items = response.get('Items', [])
            
            # Delete each item
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'sessionId': item['sessionId'],
                            'timestamp': item['timestamp']
                        }
                    )
            
            print(f'Cleared session: {session_id} ({len(items)} messages)')
            return True
        
        except Exception as e:
            print(f'Error clearing session: {str(e)}')
            return False
