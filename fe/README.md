# ProcessApp RAG - Frontend

Modern Next.js 14 chat interface for AWS Bedrock RAG agent with real-time WebSocket streaming. Supports standalone usage and embeddable widget.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create `.env.local`:

```env
NEXT_PUBLIC_WS_URL=wss://your-websocket-url.execute-api.us-east-1.amazonaws.com/dev
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 📦 Features

- ✅ **Real-time streaming** - WebSocket-based streaming responses
- ✅ **Markdown rendering** - Full markdown support with syntax highlighting
- ✅ **Session management** - Maintains conversation context
- ✅ **Auto-reconnect** - Automatic WebSocket reconnection
- ✅ **Dark mode** - Tokyo Night theme with auto dark mode
- ✅ **Responsive** - Mobile and desktop optimized
- ✅ **Embeddable** - Widget mode for iframe embedding
- ✅ **TypeScript** - Full type safety

---

## 🏗️ Project Structure

```
fe/
├── app/
│   ├── page.tsx           # Main chat page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles (Tokyo Night theme)
├── components/
│   ├── chat.tsx           # Main chat component
│   ├── chat-widget.tsx    # Embeddable widget (React)
│   └── markdown-message.tsx # Markdown renderer
├── hooks/
│   └── useWebSocketChat.ts # WebSocket connection hook
├── public/
│   └── embed.js           # Vanilla JS embed script
├── .env.local            # Environment variables (create this)
└── tailwind.config.js    # Tailwind configuration
```

---

## 📖 Usage

### Standalone Application

Visit `/` for the full chat interface with header and branding.

### Embedded Widget (React/Next.js)

```tsx
import { ChatWidget } from '@/components/chat-widget';

export default function YourPage() {
  return (
    <>
      <YourContent />
      <ChatWidget
        baseUrl="https://your-deployed-app.vercel.app"
        position="bottom-right"
      />
    </>
  );
}
```

### Embedded Widget (Vanilla HTML)

```html
<!DOCTYPE html>
<html>
<body>
  <h1>Your Website</h1>
  
  <!-- Chat Widget -->
  <script src="https://your-deployed-app.vercel.app/embed.js"></script>
  <script>
    ProcessAppChat.init({
      baseUrl: 'https://your-deployed-app.vercel.app',
      position: 'bottom-right'
    });
  </script>
</body>
</html>
```

---

## 🔌 WebSocket Integration

### Connection

The frontend connects directly to AWS API Gateway WebSocket.

**Message format (send):**
```json
{
  "question": "What documents do you have?",
  "sessionId": "unique-session-id"
}
```

**Response format (receive):**
```json
{"type": "chunk", "data": "I "}
{"type": "chunk", "data": "have "}
{"type": "chunk", "data": "documents..."}
{"type": "complete"}
```

### Hook Usage

```tsx
import { useWebSocketChat } from '@/hooks/useWebSocketChat';

function ChatComponent() {
  const { messages, isLoading, isConnected, sendMessage } = useWebSocketChat();
  
  return (
    // Your chat UI
  );
}
```

---

## 🚀 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Add environment variable in Vercel dashboard:
# NEXT_PUBLIC_WS_URL=wss://your-websocket-url...

# Deploy to production
vercel --prod
```

### Other Platforms

This Next.js app can be deployed to:
- **Netlify**: Use Next.js plugin
- **AWS Amplify**: Connect Git repo
- **Railway/Render**: Connect Git repo
- **Self-hosted**: `npm run build && npm run start`

---

## 🎨 Customization

### Theme Colors

Edit `app/globals.css` to change Tokyo Night colors:

```css
@theme {
  --color-accent-primary: #7aa2f7;    /* Blue */
  --color-accent-tertiary: #7dcfff;   /* Cyan */
  /* ... other colors */
}
```

### Branding

Edit `app/page.tsx`:

```tsx
<h1>Your Company Name</h1>
<p>Your tagline</p>
```

---

## 🧪 Testing

### Test WebSocket Connection

Open browser DevTools console and look for:
```
WebSocket connected
```

### Test with wscat

```bash
npm install -g wscat
wscat -c wss://your-websocket-url...

# Send:
{"question":"Hello","sessionId":"test-123"}
```

---

## 🐛 Troubleshooting

### WebSocket Connection Fails

Check `.env.local` has correct WebSocket URL:
```bash
echo $NEXT_PUBLIC_WS_URL
```

Test WebSocket directly:
```bash
wscat -c wss://your-url...
```

### No Streaming Responses

Check browser DevTools → Network → WS tab for WebSocket messages.

### Styles Not Loading

Clear Next.js cache and restart:
```bash
rm -rf .next
npm run dev
```

---

## 📚 Tech Stack

- **Next.js 14** - App Router
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Styling
- **React Markdown** - Message rendering
- **Lucide React** - Icons
- **WebSocket API** - Real-time communication

---

## 📝 License

Internal use - ProcessApp infrastructure

---

**Built with Next.js 14 and AWS Bedrock**
