'use client';

import { useEffect, useState } from 'react';

export default function TestPage() {
  const [status, setStatus] = useState<string>('Initializing...');
  const [messages, setMessages] = useState<string[]>([]);
  const [response, setResponse] = useState<string>('');

  useEffect(() => {
    const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev';

    setStatus(`Connecting to: ${WS_URL}`);
    addMessage(`🔌 Attempting connection to: ${WS_URL}`);

    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setStatus('✅ Connected!');
        addMessage('✅ WebSocket connected successfully!');

        // Send test message
        const testMessage = {
          question: 'What documents do you have?',
          sessionId: 'test-browser-' + Date.now()
        };

        addMessage(`📤 Sending test message: ${JSON.stringify(testMessage, null, 2)}`);
        ws?.send(JSON.stringify(testMessage));
        addMessage('📥 Waiting for response...');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'chunk') {
            setResponse((prev) => prev + data.data);
            addMessage(`📨 Received chunk: ${data.data.substring(0, 50)}...`);
          } else if (data.type === 'complete') {
            setStatus('✅ Response complete!');
            addMessage('✅ Response complete!');
          } else if (data.type === 'error') {
            setStatus(`❌ Error: ${data.message}`);
            addMessage(`❌ Error: ${data.message}`);
          }
        } catch (error) {
          addMessage(`⚠️ Failed to parse message: ${error}`);
        }
      };

      ws.onerror = (error) => {
        setStatus('❌ Connection error');
        addMessage(`❌ WebSocket error occurred`);
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        setStatus('🔌 Connection closed');
        addMessage('🔌 WebSocket connection closed');
      };
    } catch (error) {
      setStatus(`❌ Failed to create WebSocket: ${error}`);
      addMessage(`❌ Failed to create WebSocket: ${error}`);
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const addMessage = (msg: string) => {
    setMessages((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          🧪 WebSocket Connection Test
        </h1>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Connection Status
          </h2>
          <p className="text-lg font-mono text-gray-700 dark:text-gray-300">
            {status}
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Messages Log
          </h2>
          <div className="bg-gray-100 dark:bg-gray-900 rounded p-4 h-64 overflow-y-auto font-mono text-sm">
            {messages.map((msg, idx) => (
              <div key={idx} className="text-gray-700 dark:text-gray-300 mb-1">
                {msg}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Response Content
          </h2>
          <div className="bg-gray-100 dark:bg-gray-900 rounded p-4 h-96 overflow-y-auto">
            <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {response || 'Waiting for response...'}
            </p>
          </div>
          <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
            Response length: {response.length} characters
          </div>
        </div>

        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            ℹ️ Test Information
          </h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>• This page tests the WebSocket connection to AWS API Gateway</li>
            <li>• Connection is automatic on page load</li>
            <li>• Check the Messages Log for detailed connection events</li>
            <li>• Response Content shows the streaming data from the agent</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
