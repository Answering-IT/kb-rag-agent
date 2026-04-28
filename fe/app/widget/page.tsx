import { Chat } from '@/components/chat';

/**
 * Widget page - Minimal chat interface for embedding
 * Use this in an iframe for embedding in other applications
 */
export default function WidgetPage() {
  return (
    <div className="h-screen w-full bg-transparent">
      <Chat className="h-full" placeholder="How can I help you?" />
    </div>
  );
}
