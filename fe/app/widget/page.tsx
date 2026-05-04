'use client';

import { useEffect, useState } from 'react';
import { Chat } from '@/components/chat';
import { StreamingChatConfig } from '@/hooks/useStreamingChat';
import { getTranslations } from '@/lib/translations';
import { useMetadata } from '@/contexts/MetadataContext';

interface WidgetMessage {
  type: 'INIT' | 'SEND_MESSAGE';
  data?: any;
}

/**
 * Widget page - Embeddable chat interface with postMessage API
 *
 * Communication protocol:
 * 1. Parent -> Widget: INIT (with config: wsUrl, authToken, userId, etc.)
 * 2. Widget -> Parent: WIDGET_READY
 * 3. Widget -> Parent: MESSAGE_SENT (when user sends message)
 * 4. Widget -> Parent: MESSAGE_RECEIVED (when assistant responds)
 * 5. Widget -> Parent: CONNECTION_CHANGE (when WebSocket connects/disconnects)
 */
export default function WidgetPage() {
  const t = getTranslations();
  const { setMetadata } = useMetadata(); // Get metadata setter from context
  const [config, setConfig] = useState<StreamingChatConfig | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [inIframe, setInIframe] = useState<boolean | null>(null); // null = not yet determined

  useEffect(() => {
    // Prevent SSR errors
    if (typeof window === 'undefined') {
      return;
    }

    // Check if running in iframe or standalone
    const inIframe = window.self !== window.top;
    setInIframe(inIframe);

    // If standalone (not in iframe), initialize immediately
    if (!inIframe) {
      console.log('[Widget] Running in standalone mode');
      setIsStandalone(true);
      setConfig({});
      setIsReady(true);
      return;
    }

    // Timeout to fallback to standalone if no INIT received in 3 seconds
    const initTimeout = setTimeout(() => {
      console.log('[Widget] No INIT message received, falling back to standalone mode');
      setIsStandalone(true);
      setConfig({});
      setIsReady(true);
    }, 3000);

    // Listen for messages from parent window
    const handleMessage = (event: MessageEvent<WidgetMessage>) => {
      // TODO: Validate event.origin for security in production
      // For example: if (event.origin !== 'https://your-angular-app.com') return;

      if (event.data.type === 'INIT') {
        console.log('[Widget] Received INIT message');
        clearTimeout(initTimeout);

        const initData = event.data.data || {};

        const newConfig: StreamingChatConfig = {
          apiUrl: initData.apiUrl || initData.wsUrl, // Support both old wsUrl and new apiUrl for backward compatibility
          authToken: initData.authToken,
          userId: initData.userId,
          sessionId: initData.sessionId,
          headers: initData.headers,
          metadata: initData.metadata,

          // Emit events back to parent window
          onMessageSent: (message) => {
            window.parent.postMessage(
              {
                type: 'MESSAGE_SENT',
                data: message,
              },
              '*' // TODO: Replace with specific origin in production
            );
          },
          onMessageReceived: (message) => {
            window.parent.postMessage(
              {
                type: 'MESSAGE_RECEIVED',
                data: message,
              },
              '*' // TODO: Replace with specific origin in production
            );
          },
          onConnectionChange: (connected) => {
            window.parent.postMessage(
              {
                type: 'CONNECTION_CHANGE',
                data: { connected },
              },
              '*' // TODO: Replace with specific origin in production
            );
          },
        };

        setConfig(newConfig);
        setIsReady(true);

        // Store metadata in context for persistence across messages
        if (initData.metadata) {
          console.log('[Widget] Storing metadata in context:', initData.metadata);
          setMetadata(initData.metadata);
        }

        // Notify parent that widget is ready
        window.parent.postMessage(
          {
            type: 'WIDGET_READY',
            data: {},
          },
          '*' // TODO: Replace with specific origin in production
        );
      } else if (event.data.type === 'UPDATE_METADATA') {
        // 🆕 Handle dynamic metadata updates from parent (route changes)
        console.log('[Widget] Received UPDATE_METADATA message');
        const updateData = event.data.data || {};

        if (updateData.metadata) {
          console.log('[Widget] Updating metadata in context:', updateData.metadata);
          setMetadata(updateData.metadata);
        }
      }
    };

    window.addEventListener('message', handleMessage);

    // Signal to parent that widget is loaded and waiting for INIT
    window.parent.postMessage(
      {
        type: 'WIDGET_LOADED',
        data: {},
      },
      '*' // TODO: Replace with specific origin in production
    );

    return () => {
      clearTimeout(initTimeout);
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  if (!isReady || !config) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-primary mx-auto mb-4"></div>
          <p className="text-foreground-secondary">{t.initializingWidget}</p>
          <p className="text-xs text-foreground-secondary mt-2">
            {inIframe === true ? t.waitingForParent : t.loading}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background">
      {isStandalone && (
        <div className="bg-yellow-500/10 border-b border-yellow-500/20 px-4 py-2 text-xs text-yellow-600 dark:text-yellow-400">
          {t.standaloneMode}
        </div>
      )}
      <Chat config={config} className="h-full" placeholder={t.widgetPlaceholder} />
    </div>
  );
}
