# ProcessApp RAG - Frontend

Modern Next.js 14 bilingual chat interface for AWS Bedrock RAG agent with dual-mode connectivity (WebSocket/REST). Supports standalone usage and embeddable widget.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create `.env.local` (see `.env.local.example` for full template):

```env
# WebSocket API endpoint (Agent V2 - Agent Core Runtime)
NEXT_PUBLIC_WS_URL=wss://your-websocket-url.execute-api.us-east-1.amazonaws.com/dev

# REST Streaming API endpoint (Lambda Function URL)
NEXT_PUBLIC_STREAMING_API_URL=https://your-lambda-url.lambda-url.us-east-1.on.aws/

# Connection mode: 'websocket' or 'streaming' (default: websocket)
NEXT_PUBLIC_CHAT_MODE=websocket

# Show connection mode selector (default: false, always visible on /test)
NEXT_PUBLIC_SHOW_MODE_SELECTOR=false

# Language: 'es' (Spanish) or 'en' (English) - default: es
NEXT_PUBLIC_LANGUAGE=es
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## 📦 Features

- ✅ **Dual connectivity** - WebSocket (default) and REST streaming modes
- ✅ **Bilingual interface** - Spanish (default) and English support
- ✅ **Real-time streaming** - Server-sent streaming responses
- ✅ **Markdown rendering** - Full markdown support with syntax highlighting
- ✅ **Session management** - Maintains conversation context
- ✅ **Auto-reconnect** - Automatic WebSocket reconnection (WebSocket mode)
- ✅ **Dark mode** - Tokyo Night theme with auto dark mode
- ✅ **Responsive** - Mobile and desktop optimized
- ✅ **Embeddable** - Widget mode for iframe embedding with postMessage API
- ✅ **TypeScript** - Full type safety
- ✅ **Version tracking** - Built-in version display (v0.0.1)
- ✅ **Test mode** - Developer test page with connection mode toggle

---

## 🏗️ Project Structure

```
fe/
├── app/
│   ├── page.tsx           # Main chat page (standalone)
│   ├── widget/page.tsx    # Widget page (embeddable via iframe)
│   ├── test/page.tsx      # Test page (connection mode toggle)
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles (Tokyo Night theme)
├── components/
│   ├── chat.tsx           # Main chat component (used by all pages)
│   ├── chat-widget.tsx    # Embeddable widget wrapper (React)
│   └── markdown-message.tsx # Markdown renderer
├── hooks/
│   ├── useChat.ts         # Unified chat hook (mode selector)
│   ├── useWebSocketChat.ts # WebSocket connection hook
│   └── useStreamingChat.ts # REST streaming hook
├── lib/
│   └── translations.ts    # Translation strings (ES/EN) + version
├── public/
│   └── embed.js           # Vanilla JS embed script
├── .env.local            # Environment variables (create from example)
├── .env.local.example    # Environment variables template
└── tailwind.config.js    # Tailwind configuration
```

---

## 🌍 Language Configuration

The application supports **Spanish (default)** and **English** via the `NEXT_PUBLIC_LANGUAGE` environment variable.

### Available Languages

| Code | Language | Status |
|------|----------|--------|
| `es` | Español (Spanish) | ✅ Default |
| `en` | English | ✅ Available |

### Switching Languages

**Option 1: Environment Variable (Recommended)**

Edit `.env.local`:
```env
NEXT_PUBLIC_LANGUAGE=en  # English
# or
NEXT_PUBLIC_LANGUAGE=es  # Spanish (default)
```

Restart dev server after changing.

**Option 2: Add New Languages**

Edit `lib/translations.ts`:
```typescript
export type Language = 'es' | 'en' | 'pt';  // Add Portuguese

export const translations: Record<Language, Translations> = {
  es: { /* Spanish strings */ },
  en: { /* English strings */ },
  pt: { /* Portuguese strings */ },  // Add translations
};
```

### Translation Coverage

All user-facing text is translated including:
- Chat interface (headings, buttons, placeholders)
- Connection status messages
- Widget loading states
- Version label

---

## 🔄 Connection Modes

The application supports two connection modes:

### WebSocket Mode (Default)

- **Pros:** True real-time bidirectional connection, persistent connection
- **Cons:** Some corporate firewalls may block WebSocket
- **Endpoint:** `NEXT_PUBLIC_WS_URL`

### REST Streaming Mode

- **Pros:** Works with all firewalls, simpler infrastructure
- **Cons:** One-way streaming, new connection per message
- **Endpoint:** `NEXT_PUBLIC_STREAMING_API_URL`

### Changing Modes

**For Production/Users:**

Connection mode selector is **hidden by default** (cleaner UI). To show it:

```env
NEXT_PUBLIC_SHOW_MODE_SELECTOR=true
```

**For Testing/Development:**

Visit `/test` page - connection mode selector is always visible for testing both modes.

**Set Default Mode:**

```env
NEXT_PUBLIC_CHAT_MODE=websocket  # WebSocket (default)
# or
NEXT_PUBLIC_CHAT_MODE=streaming  # REST streaming
```

---

## 📖 Usage

### Standalone Application

Visit `/` for the full chat interface with header and branding.

**Routes:**
- `/` - Main chat interface (production)
- `/widget` - Widget page (for iframe embedding)
- `/test` - Test page (connection mode toggle visible)

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

## 🔌 API Integration

### WebSocket Mode (Default)

Connects to AWS API Gateway WebSocket (Agent V2 - Agent Core Runtime).

**Connection:**
```
wss://your-id.execute-api.us-east-1.amazonaws.com/dev
```

**Message format (send):**
```json
{
  "action": "message",
  "question": "¿Qué documentos tienes?",
  "sessionId": "unique-session-id"
}
```

**Response format (receive):**
```json
{"type": "chunk", "data": "Tengo "}
{"type": "chunk", "data": "documentos..."}
{"type": "complete"}
```

### REST Streaming Mode

Connects to Lambda Function URL with response streaming.

**Endpoint:**
```
https://your-id.lambda-url.us-east-1.on.aws/
```

**Request (POST):**
```json
{
  "prompt": "¿Qué documentos tienes?",
  "sessionId": "unique-session-id"
}
```

**Response:** Server-sent text chunks via ReadableStream.

### Hook Usage

**Unified Hook (Recommended):**
```tsx
import { useChat } from '@/hooks/useChat';

function ChatComponent() {
  const { messages, isLoading, isConnected, sendMessage } = useChat({
    mode: 'websocket'  // or 'streaming'
  });
  
  return (
    // Your chat UI
  );
}
```

**Mode-Specific Hooks:**
```tsx
// WebSocket
import { useWebSocketChat } from '@/hooks/useWebSocketChat';

// REST Streaming
import { useStreamingChat } from '@/hooks/useStreamingChat';
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

## 🏷️ Version Management

The application version is centrally managed in `lib/translations.ts`:

```typescript
export const APP_VERSION = 'v0.0.1';
```

The version is displayed at the bottom of the chat interface (below the input field).

**To update the version:**
1. Edit `lib/translations.ts`
2. Change `APP_VERSION` constant
3. Version updates automatically across the app

---

## 🐛 Troubleshooting

### WebSocket Connection Fails

1. **Check environment variable:**
   ```bash
   cat .env.local | grep WS_URL
   ```

2. **Test WebSocket directly:**
   ```bash
   npm install -g wscat
   wscat -c wss://your-url.execute-api.us-east-1.amazonaws.com/dev
   ```

3. **Try REST mode instead:**
   ```env
   NEXT_PUBLIC_CHAT_MODE=streaming
   ```

### Connection Mode Selector Not Showing

The selector is **intentionally hidden** on production pages for cleaner UI.

- **To show selector everywhere:** Set `NEXT_PUBLIC_SHOW_MODE_SELECTOR=true` in `.env.local`
- **To test both modes:** Visit `/test` page (selector always visible)

### Spanish/English Text Not Changing

1. **Check environment variable:**
   ```bash
   cat .env.local | grep LANGUAGE
   ```

2. **Restart dev server** after changing `.env.local`

3. **Clear browser cache** and hard reload (Ctrl+Shift+R)

### No Streaming Responses

1. **WebSocket mode:** Check DevTools → Network → WS tab for WebSocket messages
2. **REST mode:** Check DevTools → Network → Fetch/XHR for streaming requests
3. **Backend logs:** Check CloudWatch logs for Agent V2 runtime

### Styles Not Loading

Clear Next.js cache and restart:
```bash
rm -rf .next
npm run dev
```

### Widget Not Receiving Messages

1. **Check postMessage origin validation** in `app/widget/page.tsx`
2. **Check parent window** sends INIT message with correct format
3. **Check browser console** for `[Widget]` debug logs

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
