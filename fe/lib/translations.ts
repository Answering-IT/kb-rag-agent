export type Language = 'es' | 'en';

export const APP_VERSION = 'v0.0.1';

export interface Translations {
  connectionMode: string;
  rest: string;
  websocket: string;
  connectingToServer: string;
  startConversation: string;
  startConversationDesc: string;
  connectedReady: string;
  connecting: string;
  askPlaceholder: string;
  send: string;
  version: string;
}

export const translations: Record<Language, Translations> = {
  es: {
    connectionMode: 'Modo de Conexión:',
    rest: 'REST',
    websocket: 'WebSocket',
    connectingToServer: 'Conectando al servidor...',
    startConversation: 'Inicia una conversación',
    startConversationDesc: 'Pregúntame lo que quieras sobre tus documentos.',
    connectedReady: 'Conectado y listo',
    connecting: 'Conectando...',
    askPlaceholder: 'Pregúntame lo que quieras...',
    send: 'Enviar',
    version: 'Versión',
  },
  en: {
    connectionMode: 'Connection Mode:',
    rest: 'REST',
    websocket: 'WebSocket',
    connectingToServer: 'Connecting to server...',
    startConversation: 'Start a conversation',
    startConversationDesc: 'Ask me anything about your documents. I\'ll provide detailed answers powered by AWS Bedrock.',
    connectedReady: 'Connected and ready',
    connecting: 'Connecting...',
    askPlaceholder: 'Ask me anything...',
    send: 'Send',
    version: 'Version',
  },
};

export function getTranslations(lang?: string): Translations {
  const language = (lang || process.env.NEXT_PUBLIC_LANGUAGE || 'es') as Language;
  return translations[language] || translations.es;
}
