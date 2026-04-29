'use client';

import { useRef, useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { Send, Bot, User, WifiOff, Radio, Zap } from 'lucide-react';
import { useChat, ChatMode, ChatConfig } from '@/hooks/useChat';
import { MarkdownMessage } from './markdown-message';
import { getTranslations, APP_VERSION } from '@/lib/translations';

interface ChatProps {
  className?: string;
  placeholder?: string;
  config?: ChatConfig;
  showModeSelector?: boolean;
}

export function Chat({
  className = '',
  placeholder,
  config,
  showModeSelector = true
}: ChatProps) {
  const pathname = usePathname();
  const t = getTranslations();

  // Always show mode selector on test page, otherwise respect environment variable
  const shouldShowSelector = pathname === '/test'
    ? true
    : (process.env.NEXT_PUBLIC_SHOW_MODE_SELECTOR === 'true');

  // Set translated placeholder
  const actualPlaceholder = placeholder || t.askPlaceholder;

  // Read default mode from env var (defaults to 'websocket')
  const defaultMode = (process.env.NEXT_PUBLIC_CHAT_MODE as ChatMode) || 'websocket';
  const [mode, setMode] = useState<ChatMode>(config?.mode || defaultMode);
  const { messages, isLoading, isConnected, sendMessage } = useChat({ ...config, mode });
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    sendMessage(input);
    setInput('');
  };

  return (
    <div className={`flex flex-col h-full bg-background-secondary dark:bg-background ${className}`}>
      {/* Mode selector */}
      {shouldShowSelector && (
        <div className="border-b border-border-light dark:border-border-dark bg-background px-4 py-2 flex items-center justify-between">
          <span className="text-xs text-foreground-secondary font-medium">{t.connectionMode}</span>
          <div className="flex gap-1 bg-background-secondary dark:bg-background/50 p-1 rounded-lg">
            <button
              onClick={() => setMode('streaming')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'streaming'
                  ? 'bg-accent-primary text-white shadow-sm'
                  : 'text-foreground-secondary hover:text-foreground'
              }`}
            >
              <Zap className="w-3 h-3" />
              {t.rest}
            </button>
            <button
              onClick={() => setMode('websocket')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'websocket'
                  ? 'bg-accent-primary text-white shadow-sm'
                  : 'text-foreground-secondary hover:text-foreground'
              }`}
            >
              <Radio className="w-3 h-3" />
              {t.websocket}
            </button>
          </div>
        </div>
      )}

      {/* Connection status banner */}
      {!isConnected && (
        <div className="bg-accent-warning/10 dark:bg-accent-warning/5 border-b border-accent-warning/30 dark:border-accent-warning/20 px-4 py-3 flex items-center gap-3 text-accent-warning animate-pulse">
          <WifiOff className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm font-medium">{t.connectingToServer}</span>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md mx-auto">
              <div className="mb-6 inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-primary/20 to-accent-tertiary/20 dark:from-accent-primary/10 dark:to-accent-tertiary/10">
                <Bot className="w-8 h-8 text-accent-primary dark:text-accent-tertiary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{t.startConversation}</h3>
              <p className="text-sm text-foreground-secondary mb-6">{t.startConversationDesc}</p>

              {isConnected ? (
                <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-accent-success/10 dark:bg-accent-success/5 text-accent-success text-xs font-medium">
                  <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" />
                  {t.connectedReady}
                </div>
              ) : (
                <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-accent-warning/10 dark:bg-accent-warning/5 text-accent-warning text-xs font-medium">
                  <div className="w-2 h-2 rounded-full bg-accent-warning animate-pulse" />
                  {t.connecting}
                </div>
              )}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 animate-fade-in ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-accent-tertiary flex items-center justify-center shadow-md">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}

            <div
              className={`max-w-[70%] rounded-xl px-4 py-3 shadow-sm transition-all ${
                message.role === 'user'
                  ? 'bg-gradient-to-r from-accent-primary to-accent-tertiary text-white rounded-br-none'
                  : 'bg-background dark:bg-background-secondary border border-border-light dark:border-border-dark text-foreground rounded-bl-none'
              }`}
            >
              <MarkdownMessage content={message.content} isUser={message.role === 'user'} />
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary/80 to-accent-tertiary/80 flex items-center justify-center shadow-md">
                <User className="w-5 h-5 text-white" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start animate-fade-in">
            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-accent-tertiary flex items-center justify-center shadow-md">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-background dark:bg-background-secondary border border-border-light dark:border-border-dark rounded-xl px-4 py-3 shadow-sm rounded-bl-none">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-accent-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border-light dark:border-border-dark bg-background-secondary dark:bg-background/50 p-4 sm:p-6 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={actualPlaceholder}
            disabled={isLoading || !isConnected}
            className="flex-1 px-4 py-3 border border-border-light dark:border-border-dark rounded-lg focus-ring bg-background dark:bg-background-secondary text-foreground placeholder-foreground-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim() || !isConnected}
            className="px-4 py-3 bg-gradient-to-r from-accent-primary to-accent-tertiary text-white font-medium rounded-lg hover:shadow-lg hover:from-accent-primary/90 hover:to-accent-tertiary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 group"
          >
            <Send className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            <span className="hidden sm:inline">{t.send}</span>
          </button>
        </form>

        {/* Version label */}
        <div className="mt-2 text-center">
          <span className="text-xs text-foreground-secondary/60">
            {t.version} {APP_VERSION}
          </span>
        </div>
      </div>
    </div>
  );
}
