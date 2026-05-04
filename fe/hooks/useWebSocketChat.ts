import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useMetadata } from '@/contexts/MetadataContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface WebSocketChatConfig {
  wsUrl?: string;
  sessionId?: string;
  metadata?: Record<string, any>; // Direct metadata (merged with context metadata)
  onMessageSent?: (message: Message) => void;
  onMessageReceived?: (message: Message) => void;
  onConnectionChange?: (connected: boolean) => void;
}

interface UseWebSocketChatReturn {
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  sendMessage: (content: string) => void;
  sessionId: string;
}

const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_WS_URL || '';

export function useWebSocketChat(config: WebSocketChatConfig = {}): UseWebSocketChatReturn {
  const {
    wsUrl = DEFAULT_WS_URL,
    sessionId: externalSessionId,
    metadata: configMetadata, // Renamed to avoid conflict
    onMessageSent,
    onMessageReceived,
    onConnectionChange,
  } = config;

  // Use metadata from context (persistent across messages)
  const { metadata: contextMetadata } = useMetadata();

  // Merge: context metadata takes precedence, fallback to config metadata
  const metadata = { ...configMetadata, ...contextMetadata };

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId] = useState(() => externalSessionId || uuidv4());

  const wsRef = useRef<WebSocket | null>(null);
  const currentAssistantMessageRef = useRef<{ id: string; content: string } | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    console.log('[WebSocketChat] Connecting to:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocketChat] Connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        onConnectionChange?.(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocketChat] Message:', data);

          if (data.type === 'chunk' && data.data) {
            // Stream response chunk by chunk
            if (!currentAssistantMessageRef.current) {
              // Create new assistant message
              const newId = uuidv4();
              currentAssistantMessageRef.current = { id: newId, content: data.data };
              const newMessage: Message = {
                id: newId,
                role: 'assistant',
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
            console.log('[WebSocketChat] Response complete');

            // Emit onMessageReceived
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
            console.error('[WebSocketChat] Error:', data.message);
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
          console.error('[WebSocketChat] Failed to parse message:', error);
        }
      };

      ws.onclose = () => {
        console.log('[WebSocketChat] Disconnected');
        setIsConnected(false);
        onConnectionChange?.(false);

        // Attempt reconnect
        if (reconnectAttemptsRef.current < 5) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`[WebSocketChat] Reconnecting in ${delay}ms...`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (event: Event) => {
        console.error('[WebSocketChat] WebSocket error occurred');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocketChat] Connection error:', error);
    }
  }, [wsUrl, onConnectionChange, onMessageReceived]);

  const sendMessage = useCallback((content: string) => {
    if (!content.trim() || isLoading || !isConnected) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    onMessageSent?.(userMessage);

    // Send via WebSocket with persistent metadata as separate object
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const payload: Record<string, any> = {
        action: 'sendMessage',
        data: {
          inputText: content,
          sessionId: sessionId,
        }
      };

      // Add metadata as a separate object if present
      if (metadata && Object.keys(metadata).length > 0) {
        payload.data.metadata = metadata;
      }

      console.log('[WebSocketChat] Sending message with metadata:', metadata);
      wsRef.current.send(JSON.stringify(payload));
    }
  }, [isLoading, isConnected, sessionId, metadata, onMessageSent]);

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
