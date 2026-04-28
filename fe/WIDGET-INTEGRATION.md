# Widget Integration - Implementation Complete

## Overview

The Next.js chat frontend has been enhanced to support both **standalone mode** (existing functionality) and **widget mode** (embedded in Angular app) with full authentication and configuration support.

## Changes Made

### 1. Enhanced WebSocket Hook (`hooks/useWebSocketChat.ts`)

**New Features:**
- Accepts `WebSocketChatConfig` with optional parameters:
  - `wsUrl`: Custom WebSocket URL
  - `authToken`: Authentication token
  - `userId`: User ID
  - `sessionId`: Session ID (auto-generated if not provided)
  - `headers`: Custom HTTP headers
  - `metadata`: Additional metadata to send to backend
  - Event callbacks:
    - `onMessageSent`: Fired when user sends a message
    - `onMessageReceived`: Fired when assistant responds (complete message)
    - `onConnectionChange`: Fired when WebSocket connects/disconnects

**Backward Compatible:** The hook still works without any config (defaults to existing behavior)

### 2. Updated Chat Component (`components/chat.tsx`)

- Now accepts optional `config` prop of type `WebSocketChatConfig`
- Passes config to `useWebSocketChat` hook
- Fully backward compatible (works without config prop)

### 3. New Widget Page (`app/widget/page.tsx`)

**Purpose:** Embeddable page that communicates with parent window via postMessage API

**Communication Protocol:**
1. Widget sends `WIDGET_LOADED` on mount
2. Parent sends `INIT` with configuration (auth, wsUrl, etc.)
3. Widget responds with `WIDGET_READY`
4. Widget emits events during operation:
   - `MESSAGE_SENT`: User sent a message
   - `MESSAGE_RECEIVED`: Assistant responded
   - `CONNECTION_CHANGE`: WebSocket connection status changed

**Loading State:** Shows a spinner while waiting for INIT message from parent

### 4. Angular Component (`REP_FE_COLPENSIONES/src/app/shared/components/fury-chat-widget/`)

**Files Created:**
- `fury-chat-widget.component.ts` - Component logic with postMessage handling
- `fury-chat-widget.component.html` - Template with floating button and iframe
- `fury-chat-widget.component.scss` - Styles (Material Design, responsive)
- `fury-chat-widget.module.ts` - Angular module
- `README.md` - Comprehensive documentation
- `INTEGRATION-EXAMPLE.md` - Step-by-step integration guide

**Features:**
- Floating action button (bottom-right corner)
- Material Design styling
- Connection status indicator
- Automatic auth token detection from sessionStorage/localStorage
- postMessage communication with Next.js widget
- Responsive design (mobile-friendly)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Angular App (Main)                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  FuryChatWidgetComponent                              │  │
│  │  - Floating button                                    │  │
│  │  - Auth token from sessionStorage                     │  │
│  │  - postMessage: INIT → Widget                         │  │
│  │  - Listens for: MESSAGE_SENT, MESSAGE_RECEIVED, etc.  │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │         <iframe> Next.js Widget              │    │  │
│  │  │                                               │    │  │
│  │  │  /widget page (Next.js)                      │    │  │
│  │  │  - Listens for: INIT from parent             │    │  │
│  │  │  - Emits: WIDGET_READY, MESSAGE_SENT, etc.   │    │  │
│  │  │  - Loads Chat component with config          │    │  │
│  │  │                                               │    │  │
│  │  │  ┌────────────────────────────────────┐      │    │  │
│  │  │  │  Chat Component                    │      │    │  │
│  │  │  │  - useWebSocketChat(config)        │      │    │  │
│  │  │  │  - Connects to backend WebSocket   │      │    │  │
│  │  │  │  - Sends authToken, headers, etc.  │      │    │  │
│  │  │  └────────────────────────────────────┘      │    │  │
│  │  └──────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   Backend WebSocket
              (AWS API Gateway + Agent)
```

## Testing Instructions

### Step 1: Start Next.js Frontend (Standalone Mode)

```bash
cd /Users/qohatpretel/Answering/kb-rag-agent/fe
npm run dev
```

Visit: `http://localhost:3000`
- ✅ Should work as before (standalone mode)
- ✅ No auth configuration needed

### Step 2: Test Widget Page

Visit: `http://localhost:3000/widget`
- ✅ Should show "Initializing widget..." (waiting for INIT message)
- ✅ This is normal - the widget needs a parent to send INIT

### Step 3: Test Widget in Angular App

#### 3.1 Import Module in Angular

Edit `/Users/qohatpretel/Answering/REP_FE_COLPENSIONES/src/app/app.module.ts`:

```typescript
import { FuryChatWidgetModule } from './shared/components/fury-chat-widget/fury-chat-widget.module';

@NgModule({
  imports: [
    // ... existing imports
    FuryChatWidgetModule, // <-- Add this
  ],
})
export class AppModule {}
```

#### 3.2 Add Widget to Layout

Edit `/Users/qohatpretel/Answering/REP_FE_COLPENSIONES/src/app/app.component.html`:

Add at the end of the file:

```html
<fury-chat-widget
  [widgetUrl]="'http://localhost:3000/widget'"
></fury-chat-widget>
```

#### 3.3 Start Angular App

```bash
cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES
ng serve
```

Visit: `http://localhost:4200` (or your Angular dev port)

#### 3.4 Test Widget Functionality

1. ✅ **Floating Button**: Should see a purple chat button in bottom-right corner
2. ✅ **Open Widget**: Click the button → widget container should slide up
3. ✅ **Loading**: Should show a spinner briefly while iframe loads
4. ✅ **Initialization**: Widget should initialize with auth data from Angular
5. ✅ **Connection**: Connection status dot should turn green when WebSocket connects
6. ✅ **Messaging**: Type a message and send → should work like standalone mode
7. ✅ **Responses**: Assistant should respond with proper formatting
8. ✅ **Close**: Click X button or floating button → widget should close

### Step 4: Test Authentication Flow

#### 4.1 Set Auth Token in Browser Console

While on the Angular app, open browser DevTools console:

```javascript
sessionStorage.setItem('authToken', 'test-token-123');
sessionStorage.setItem('userId', 'user-456');
```

#### 4.2 Reload and Test

1. Reload the page
2. Open the widget
3. Open browser DevTools console
4. Look for log: `[Angular] Sending INIT message with config:`
5. Verify the config includes your auth token and user ID

### Step 5: Test postMessage Communication

#### 5.1 Enable Logging

Browser DevTools console should show:
```
[Angular] Widget loaded, sending INIT message
[Widget] Received INIT message from parent: {...}
[Angular] Widget ready
[Angular] User sent message: {...}
[Widget] MESSAGE_SENT event
[Angular] Assistant responded: {...}
[Widget] MESSAGE_RECEIVED event
```

#### 5.2 Verify WebSocket Payload

Open DevTools → Network → WS tab → Click on WebSocket connection → Messages

Verify that messages include auth data:
```json
{
  "question": "test question",
  "sessionId": "...",
  "authToken": "test-token-123",
  "userId": "user-456",
  "headers": { "Authorization": "Bearer test-token-123" },
  "metadata": { "userAgent": "...", "timestamp": "..." }
}
```

## File Changes Summary

### Next.js Frontend (`/Users/qohatpretel/Answering/kb-rag-agent/fe/`)

- ✅ Modified: `hooks/useWebSocketChat.ts` (added config support)
- ✅ Modified: `components/chat.tsx` (added config prop)
- ✅ Modified: `app/widget/page.tsx` (complete rewrite with postMessage)
- ✅ Created: `WIDGET-INTEGRATION.md` (this file)

### Angular App (`/Users/qohatpretel/Answering/REP_FE_COLPENSIONES/`)

- ✅ Created: `src/app/shared/components/fury-chat-widget/fury-chat-widget.component.ts`
- ✅ Created: `src/app/shared/components/fury-chat-widget/fury-chat-widget.component.html`
- ✅ Created: `src/app/shared/components/fury-chat-widget/fury-chat-widget.component.scss`
- ✅ Created: `src/app/shared/components/fury-chat-widget/fury-chat-widget.module.ts`
- ✅ Created: `src/app/shared/components/fury-chat-widget/README.md`
- ✅ Created: `src/app/shared/components/fury-chat-widget/INTEGRATION-EXAMPLE.md`

## Next Steps

1. ✅ **Test the integration** (follow testing instructions above)
2. ⏭️ **Configure production URLs** (replace localhost with production URLs)
3. ⏭️ **Add origin validation** (replace `'*'` in postMessage with specific origins)
4. ⏭️ **Backend modifications** (if needed to handle auth headers from widget)
5. ⏭️ **Styling adjustments** (customize widget appearance to match Angular app)

## Production Deployment

### Security Checklist

Before deploying to production:

1. **Origin Validation** (CRITICAL):
   - [ ] Update `fury-chat-widget.component.ts` to validate event.origin
   - [ ] Update `fe/app/widget/page.tsx` to validate event.origin
   - [ ] Replace all `'*'` with actual domain names

2. **Environment Configuration**:
   - [ ] Add `chatWidgetUrl` to environment files
   - [ ] Add `chatWsUrl` to environment files
   - [ ] Deploy Next.js app to production (e.g., Vercel)

3. **CORS Configuration**:
   - [ ] Configure backend to accept requests from Angular domain
   - [ ] Add proper CORS headers to WebSocket endpoint

4. **CSP Headers**:
   - [ ] Allow iframe embedding from Next.js domain in Angular app
   - [ ] Configure Content-Security-Policy headers

### Example Production Configuration

**Next.js (Vercel):**
- URL: `https://chat.procesapp.com`
- Widget: `https://chat.procesapp.com/widget`

**Angular App:**
```typescript
// environment.prod.ts
export const environment = {
  production: true,
  chatWidgetUrl: 'https://chat.procesapp.com/widget',
  chatWsUrl: 'wss://api.procesapp.com/ws',
};
```

**postMessage Origins:**
```typescript
// Angular side
if (event.origin !== 'https://chat.procesapp.com') return;

// Next.js side
if (event.origin !== 'https://app.procesapp.com') return;
```

## Troubleshooting

### Issue: Widget not loading
**Solution:** Check browser console for CORS errors, verify iframe src URL

### Issue: Widget stuck on "Initializing..."
**Solution:** Check postMessage communication in console, verify INIT message is sent

### Issue: Authentication not working
**Solution:** Verify sessionStorage has auth tokens, check console logs for config data

### Issue: WebSocket connection fails
**Solution:** Check `wsUrl` is correct, verify backend is running, check Network tab for WS

### Issue: Messages not sending
**Solution:** Check WebSocket connection status, verify auth headers are correct

## Support

For detailed integration instructions, see:
- `REP_FE_COLPENSIONES/src/app/shared/components/fury-chat-widget/README.md`
- `REP_FE_COLPENSIONES/src/app/shared/components/fury-chat-widget/INTEGRATION-EXAMPLE.md`
