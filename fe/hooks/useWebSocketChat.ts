import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface UseWebSocketChatReturn {
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  sendMessage: (content: string) => void;
  sessionId: string;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev';

export function useWebSocketChat(): UseWebSocketChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId] = useState(() => uuidv4());

  const wsRef = useRef<WebSocket | null>(null);
  const currentAssistantMessageRef = useRef<{ id: string } | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'chunk' && data.data) {
            // Stream response chunk by chunk
            if (!currentAssistantMessageRef.current) {
              // Create new assistant message
              const newId = uuidv4();
              currentAssistantMessageRef.current = { id: newId };
              setMessages((prev) => [
                ...prev,
                {
                  id: newId,
                  role: 'assistant',
                  content: data.data,
                },
              ]);
            } else {
              // Append chunk to existing message
              const messageId = currentAssistantMessageRef.current.id;
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
            console.log('Response complete');
            currentAssistantMessageRef.current = null;
            setIsLoading(false);
          } else if (data.type === 'error') {
            console.error('WebSocket error:', data.message);
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
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;

        // Auto-reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, 3000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setIsConnected(false);
    }
  }, []);

  const sendMessage = useCallback((content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Ensure connection
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connect();
      // Wait for connection before sending
      const checkConnection = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          clearInterval(checkConnection);
          sendToWebSocket(content);
        }
      }, 100);

      // Timeout after 5 seconds
      setTimeout(() => {
        clearInterval(checkConnection);
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          const errorMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: 'Failed to connect to the server. Please try again.',
          };
          setMessages((prev) => [...prev, errorMessage]);
          setIsLoading(false);
        }
      }, 5000);
    } else {
      sendToWebSocket(content);
    }
  }, [isLoading, connect]);

  const sendToWebSocket = (content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }

    const message = {
      question: content,
      sessionId: sessionId,
    };

    try {
      wsRef.current.send(JSON.stringify(message));
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Failed to send message. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    messages,
    isLoading,
    isConnected,
    sendMessage,
    sessionId,
  };
}
