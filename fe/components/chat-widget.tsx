'use client';

import { useState } from 'react';
import { MessageCircle, X, Minimize2 } from 'lucide-react';

interface ChatWidgetProps {
  /**
   * The URL of your deployed Next.js app
   * Example: 'https://your-app.vercel.app'
   */
  baseUrl: string;

  /**
   * Position of the widget button
   * @default 'bottom-right'
   */
  position?: 'bottom-right' | 'bottom-left';

  /**
   * Custom button color
   * @default 'blue'
   */
  buttonColor?: string;
}

/**
 * ChatWidget component
 *
 * This component can be used to embed the chat in any React/Next.js application.
 * It displays a floating button that opens the chat in a modal overlay.
 *
 * Usage:
 * ```tsx
 * import { ChatWidget } from '@/components/chat-widget';
 *
 * export default function YourPage() {
 *   return (
 *     <>
 *       <YourContent />
 *       <ChatWidget baseUrl="https://your-chat-app.vercel.app" />
 *     </>
 *   );
 * }
 * ```
 */
export function ChatWidget({
  baseUrl,
  position = 'bottom-right',
  buttonColor = '#3B82F6',
}: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  const positionClasses = {
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  };

  return (
    <>
      {/* Floating button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className={`fixed ${positionClasses[position]} z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
          style={{ backgroundColor: buttonColor }}
          aria-label="Open chat"
        >
          <MessageCircle className="w-6 h-6 text-white" />
        </button>
      )}

      {/* Chat modal */}
      {isOpen && (
        <div
          className={`fixed ${positionClasses[position]} z-50 transition-all duration-300 ${
            isMinimized ? 'w-80 h-14' : 'w-96 h-[600px]'
          }`}
        >
          {/* Header */}
          <div
            className="absolute top-0 left-0 right-0 h-14 rounded-t-lg shadow-lg flex items-center justify-between px-4"
            style={{ backgroundColor: buttonColor }}
          >
            <div className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 text-white" />
              <span className="text-white font-semibold">
                {isMinimized ? 'Chat (minimized)' : 'Chat with us'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="text-white hover:bg-white/20 p-1 rounded transition-colors"
                aria-label={isMinimized ? 'Maximize' : 'Minimize'}
              >
                <Minimize2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-white hover:bg-white/20 p-1 rounded transition-colors"
                aria-label="Close chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Chat iframe */}
          {!isMinimized && (
            <iframe
              src={`${baseUrl}/widget`}
              className="w-full h-full rounded-b-lg shadow-lg border-0"
              title="Chat widget"
              allow="clipboard-write"
            />
          )}
        </div>
      )}
    </>
  );
}
