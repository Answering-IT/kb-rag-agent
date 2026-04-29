import { useWebSocketChat, WebSocketChatConfig } from './useWebSocketChat';
import { useStreamingChat, StreamingChatConfig } from './useStreamingChat';

export type ChatMode = 'websocket' | 'streaming';

export interface ChatConfig {
  mode?: ChatMode;
  sessionId?: string;
  onMessageSent?: (message: any) => void;
  onMessageReceived?: (message: any) => void;
  onConnectionChange?: (connected: boolean) => void;
}

const DEFAULT_MODE = (process.env.NEXT_PUBLIC_CHAT_MODE as ChatMode) || 'streaming';

/**
 * Unified chat hook that supports both WebSocket and REST streaming
 */
export function useChat(config: ChatConfig = {}) {
  const mode = config.mode || DEFAULT_MODE;

  const wsChat = useWebSocketChat({
    sessionId: config.sessionId,
    onMessageSent: config.onMessageSent,
    onMessageReceived: config.onMessageReceived,
    onConnectionChange: config.onConnectionChange,
  });

  const streamingChat = useStreamingChat({
    sessionId: config.sessionId,
    onMessageSent: config.onMessageSent,
    onMessageReceived: config.onMessageReceived,
    onConnectionChange: config.onConnectionChange,
  });

  return mode === 'websocket' ? wsChat : streamingChat;
}
