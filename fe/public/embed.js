/**
 * ProcessApp RAG Chat Widget Embed Script
 *
 * This script allows you to embed the chat widget in any HTML page.
 *
 * Usage:
 * 1. Add this script to your HTML:
 *    <script src="https://your-app.vercel.app/embed.js"></script>
 *
 * 2. Initialize the widget:
 *    <script>
 *      ProcessAppChat.init({
 *        baseUrl: 'https://your-app.vercel.app',
 *        position: 'bottom-right', // or 'bottom-left'
 *        buttonColor: '#3B82F6', // optional
 *      });
 *    </script>
 */

(function() {
  'use strict';

  // Prevent multiple initializations
  if (window.ProcessAppChat) {
    return;
  }

  window.ProcessAppChat = {
    init: function(config) {
      const baseUrl = config.baseUrl || window.location.origin;
      const position = config.position || 'bottom-right';
      const buttonColor = config.buttonColor || '#3B82F6';

      // Create container
      const container = document.createElement('div');
      container.id = 'processapp-chat-widget';
      document.body.appendChild(container);

      // State
      let isOpen = false;
      let isMinimized = false;

      // Position classes
      const positionStyles = {
        'bottom-right': 'bottom: 16px; right: 16px;',
        'bottom-left': 'bottom: 16px; left: 16px;',
      };

      // Create button
      function createButton() {
        return `
          <button
            id="processapp-chat-button"
            style="
              position: fixed;
              ${positionStyles[position]}
              z-index: 9999;
              width: 56px;
              height: 56px;
              border-radius: 50%;
              background-color: ${buttonColor};
              border: none;
              box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
              cursor: pointer;
              display: flex;
              align-items: center;
              justify-content: center;
              transition: transform 0.2s;
            "
            onmouseover="this.style.transform='scale(1.1)'"
            onmouseout="this.style.transform='scale(1)'"
            aria-label="Open chat"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </button>
        `;
      }

      // Create modal
      function createModal() {
        const height = isMinimized ? '56px' : '600px';
        return `
          <div
            id="processapp-chat-modal"
            style="
              position: fixed;
              ${positionStyles[position]}
              z-index: 9999;
              width: 384px;
              height: ${height};
              transition: height 0.3s;
            "
          >
            <!-- Header -->
            <div
              style="
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 56px;
                background-color: ${buttonColor};
                border-radius: 8px 8px 0 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 16px;
                color: white;
              "
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span style="font-weight: 600;">
                  ${isMinimized ? 'Chat (minimized)' : 'Chat with us'}
                </span>
              </div>
              <div style="display: flex; gap: 8px;">
                <button
                  id="processapp-chat-minimize"
                  style="
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                    cursor: pointer;
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                  "
                  aria-label="Minimize"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <polyline points="4 14 10 14 10 20"></polyline>
                    <polyline points="20 10 14 10 14 4"></polyline>
                    <line x1="14" y1="10" x2="21" y2="3"></line>
                    <line x1="3" y1="21" x2="10" y2="14"></line>
                  </svg>
                </button>
                <button
                  id="processapp-chat-close"
                  style="
                    background: rgba(255, 255, 255, 0.2);
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                    cursor: pointer;
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                  "
                  aria-label="Close"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Chat iframe -->
            ${
              !isMinimized
                ? `
              <iframe
                src="${baseUrl}/widget"
                style="
                  width: 100%;
                  height: calc(100% - 56px);
                  border: none;
                  border-radius: 0 0 8px 8px;
                  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                  margin-top: 56px;
                "
                title="Chat widget"
                allow="clipboard-write"
              ></iframe>
            `
                : ''
            }
          </div>
        `;
      }

      // Render
      function render() {
        container.innerHTML = isOpen ? createModal() : createButton();

        // Attach event listeners
        if (!isOpen) {
          document
            .getElementById('processapp-chat-button')
            .addEventListener('click', function() {
              isOpen = true;
              render();
            });
        } else {
          document
            .getElementById('processapp-chat-close')
            .addEventListener('click', function() {
              isOpen = false;
              isMinimized = false;
              render();
            });

          document
            .getElementById('processapp-chat-minimize')
            .addEventListener('click', function() {
              isMinimized = !isMinimized;
              render();
            });
        }
      }

      // Initial render
      render();
    },
  };
})();
