import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface StreamingChatConfig {
  apiUrl?: string;
  authToken?: string;
  userId?: string;
  sessionId?: string;
  headers?: Record<string, string>;
  metadata?: Record<string, any>;
  onMessageSent?: (message: Message) => void;
  onMessageReceived?: (message: Message) => void;
  onConnectionChange?: (connected: boolean) => void;
}

interface UseStreamingChatReturn {
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  sendMessage: (content: string) => void;
  sessionId: string;
}

const DEFAULT_API_URL = process.env.NEXT_PUBLIC_STREAMING_API_URL || '';

export function useStreamingChat(config: StreamingChatConfig = {}): UseStreamingChatReturn {
  const {
    apiUrl = DEFAULT_API_URL,
    authToken,
    userId,
    sessionId: externalSessionId,
    headers = {},
    metadata = {},
    onMessageSent,
    onMessageReceived,
    onConnectionChange,
  } = config;

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(true); // REST is always "connected"
  const [sessionId] = useState(() => externalSessionId || uuidv4());

  const currentAssistantMessageRef = useRef<{ id: string; content: string } | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Emit onMessageSent event
    onMessageSent?.(userMessage);

    // Create abort controller for cancellation
    abortControllerRef.current = new AbortController();

    try {
      // Prepare request payload
      const requestBody: any = {
        question: content,
        sessionId: sessionId,
      };

      if (authToken) requestBody.authToken = authToken;
      if (userId) requestBody.userId = userId;
      if (Object.keys(headers).length > 0) requestBody.headers = headers;
      if (Object.keys(metadata).length > 0) requestBody.metadata = metadata;

      console.log('[StreamingChat] Sending request to:', apiUrl);

      // Make fetch request with streaming
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Read streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        // Decode chunk
        buffer += decoder.decode(value, { stream: true });

        // Process complete lines (NDJSON format)
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue;

          try {
            const data = JSON.parse(line);

            if (data.type === 'chunk' && data.data) {
              // Stream response chunk by chunk
              if (!currentAssistantMessageRef.current) {
                // Create new assistant message
                const newId = uuidv4();
                currentAssistantMessageRef.current = { id: newId, content: data.data };
                const newMessage = {
                  id: newId,
                  role: 'assistant' as const,
                  content: data.data,
                };
                setMessages((prev) => [...prev, newMessage]);
              } else {
                // Append chunk to existing message
                const messageId = currentAssistantMessageRef.current.id;
                currentAssistantMessageRef.current.content += data.data;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === messageId
                      ? { ...msg, content: msg.content + data.data }
                      : msg
                  )
                );
              }
            } else if (data.type === 'complete') {
              // Response complete
              console.log('[StreamingChat] Response complete');

              // Emit onMessageReceived with final message
              if (currentAssistantMessageRef.current) {
                const finalMessage: Message = {
                  id: currentAssistantMessageRef.current.id,
                  role: 'assistant',
                  content: currentAssistantMessageRef.current.content,
                };
                onMessageReceived?.(finalMessage);
              }

              currentAssistantMessageRef.current = null;
              setIsLoading(false);
            } else if (data.type === 'error') {
              console.error('[StreamingChat] Error:', data.message);
              const errorMessage: Message = {
                id: uuidv4(),
                role: 'assistant',
                content: `Error: ${data.message || 'An error occurred'}`,
              };
              setMessages((prev) => [...prev, errorMessage]);
              currentAssistantMessageRef.current = null;
              setIsLoading(false);
            }
          } catch (error) {
            console.error('[StreamingChat] Failed to parse line:', line, error);
          }
        }
      }

      // Ensure loading is stopped
      setIsLoading(false);

    } catch (error: any) {
      console.error('[StreamingChat] Error:', error);

      if (error.name === 'AbortError') {
        console.log('[StreamingChat] Request aborted');
      } else {
        const errorMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: `Error: ${error.message || 'Failed to connect to the server'}`,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }

      currentAssistantMessageRef.current = null;
      setIsLoading(false);
    }
  }, [apiUrl, authToken, userId, sessionId, headers, metadata, isLoading, onMessageSent, onMessageReceived]);

  return {
    messages,
    isLoading,
    isConnected,
    sendMessage,
    sessionId,
  };
}
