/**
 * Content script to capture console messages
 */

(function() {
  'use strict';

  // Global error handler for extension context invalidation
  // This catches any uncaught errors from async callbacks
  if (typeof chrome !== 'undefined' && chrome.runtime) {
    // Check context validity before doing anything
    try {
      if (!chrome.runtime.id) {
        console.debug('[MCP Browser] Extension context not available');
        return; // Exit early
      }
    } catch (e) {
      console.debug('[MCP Browser] Extension context invalidated on load');
      return; // Exit early
    }
  } else {
    console.debug('[MCP Browser] Chrome runtime not available');
    return; // Exit early
  }

  // Mark that the extension is installed (for detection)
  // Note: This won't be accessible from page context due to isolation
  window.__MCP_BROWSER_EXTENSION__ = {
    version: '1.0.0',
    installed: true,
    timestamp: new Date().toISOString()
  };

  // Add DOM marker for detection (accessible from page)
  const marker = document.createElement('div');
  marker.setAttribute('data-mcp-browser-extension', 'installed');
  marker.setAttribute('data-extension-version', '1.0.0');
  marker.style.display = 'none';
  if (document.documentElement) {
    document.documentElement.appendChild(marker);
  }

  // Also add a class to document element
  if (document.documentElement) {
    document.documentElement.classList.add('mcp-browser-extension-installed');
  }

  // Message buffer
  const messageBuffer = [];
  let bufferTimer = null;
  const BUFFER_INTERVAL = 2500; // 2.5 seconds
  const MAX_BUFFER_SIZE = 100;

  // Event listener tracking for cleanup - memory leak prevention
  const trackedListeners = [];

  function addTrackedListener(target, event, handler, options) {
    target.addEventListener(event, handler, options);
    trackedListeners.push({ target, event, handler, options });
  }

  function removeAllTrackedListeners() {
    trackedListeners.forEach(({ target, event, handler, options }) => {
      try {
        target.removeEventListener(event, handler, options);
      } catch (e) {
        // Ignore errors for removed elements
      }
    });
    trackedListeners.length = 0;
  }

  // Store original console methods
  const originalConsole = {
    log: console.log,
    warn: console.warn,
    error: console.error,
    info: console.info,
    debug: console.debug
  };

  // Check if extension context is still valid
  function isContextValid() {
    try {
      // Check if chrome and chrome.runtime exist first
      if (typeof chrome === 'undefined' || !chrome) {
        cleanupOnContextInvalidation();
        return false;
      }
      if (typeof chrome.runtime === 'undefined' || !chrome.runtime) {
        cleanupOnContextInvalidation();
        return false;
      }
      // Then check for id
      const isValid = !!chrome.runtime.id;
      if (!isValid) {
        cleanupOnContextInvalidation();
      }
      return isValid;
    } catch (e) {
      cleanupOnContextInvalidation();
      return false;
    }
  }

  // Clean up resources when extension context is invalidated - memory leak prevention
  function cleanupOnContextInvalidation() {
    // Clear message buffer to prevent memory leak
    messageBuffer.length = 0;

    // Remove all tracked event listeners
    removeAllTrackedListeners();

    // Clear buffer timer
    if (bufferTimer) {
      clearTimeout(bufferTimer);
      bufferTimer = null;
    }
  }

  // Send message to background script
  function sendToBackground(messages) {
    // Check if extension context is still valid
    if (!isContextValid()) {
      // Extension was reloaded/updated - stop trying to send messages
      console.debug('[MCP Browser] Extension context invalidated, stopping message capture');
      return;
    }

    try {
      chrome.runtime.sendMessage({
        type: 'console_messages',
        messages: messages,
        url: window.location.href,
        timestamp: new Date().toISOString()
      }, (response) => {
        // Handle potential errors silently
        if (chrome.runtime.lastError) {
          // Context invalidated - this is expected during extension reload
          console.debug('[MCP Browser] Message send failed:', chrome.runtime.lastError.message);
        }
      });
    } catch (e) {
      // Extension context invalidated
      console.debug('[MCP Browser] Extension context error:', e.message);
    }
  }

  // Flush message buffer
  function flushBuffer() {
    if (messageBuffer.length > 0) {
      sendToBackground([...messageBuffer]);
      messageBuffer.length = 0;
    }
  }

  // Schedule buffer flush
  function scheduleFlush() {
    if (bufferTimer) {
      clearTimeout(bufferTimer);
    }
    bufferTimer = setTimeout(flushBuffer, BUFFER_INTERVAL);
  }

  // Capture console method
  function captureConsoleMethod(method, level) {
    console[method] = function(...args) {
      // Call original method
      originalConsole[method].apply(console, args);

      // Create message object
      const message = {
        level: level,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        args: args.map(arg => {
          try {
            if (typeof arg === 'object') {
              return JSON.stringify(arg, null, 2);
            }
            return String(arg);
          } catch (e) {
            return '[Object]';
          }
        }),
        message: args.map(arg => {
          try {
            if (typeof arg === 'object') {
              return JSON.stringify(arg);
            }
            return String(arg);
          } catch (e) {
            return '[Object]';
          }
        }).join(' ')
      };

      // Add stack trace for errors
      if (level === 'error') {
        const error = new Error();
        message.stackTrace = error.stack;
      }

      // Add to buffer
      messageBuffer.push(message);

      // Flush if buffer is full
      if (messageBuffer.length >= MAX_BUFFER_SIZE) {
        flushBuffer();
      } else {
        scheduleFlush();
      }
    };
  }

  // Capture all console methods
  captureConsoleMethod('log', 'log');
  captureConsoleMethod('warn', 'warn');
  captureConsoleMethod('error', 'error');
  captureConsoleMethod('info', 'info');
  captureConsoleMethod('debug', 'debug');

  // Capture unhandled errors
  addTrackedListener(window, 'error', function(event) {
    const message = {
      level: 'error',
      timestamp: new Date().toISOString(),
      url: window.location.href,
      message: `${event.message}`,
      stackTrace: event.error ? event.error.stack : '',
      lineNumber: event.lineno,
      columnNumber: event.colno,
      sourceFile: event.filename
    };

    messageBuffer.push(message);
    scheduleFlush();
  });

  // Capture unhandled promise rejections
  addTrackedListener(window, 'unhandledrejection', function(event) {
    const message = {
      level: 'error',
      timestamp: new Date().toISOString(),
      url: window.location.href,
      message: `Unhandled Promise Rejection: ${event.reason}`,
      stackTrace: event.reason && event.reason.stack ? event.reason.stack : ''
    };

    messageBuffer.push(message);
    scheduleFlush();
  });

  // Flush buffer before page unload
  addTrackedListener(window, 'beforeunload', function() {
    flushBuffer();
  });

  // DOM interaction helper functions
  const domHelpers = {
    // Wait for element with timeout
    async waitForElement(selector, timeout = 5000) {
      const startTime = Date.now();

      while (Date.now() - startTime < timeout) {
        const element = document.querySelector(selector);
        if (element) return element;
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      throw new Error(`Element not found: ${selector}`);
    },

    // Get element by various methods
    getElement(params) {
      const { selector, xpath, text, index = 0 } = params;

      if (selector) {
        const elements = document.querySelectorAll(selector);
        return elements[index] || null;
      }

      if (xpath) {
        const result = document.evaluate(
          xpath,
          document,
          null,
          XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
          null
        );
        return result.snapshotItem(index);
      }

      if (text) {
        const elements = Array.from(document.querySelectorAll('*')).filter(el =>
          el.textContent && el.textContent.includes(text)
        );
        return elements[index] || null;
      }

      return null;
    },

    // Get element information
    getElementInfo(element) {
      if (!element) return null;

      const rect = element.getBoundingClientRect();
      const styles = window.getComputedStyle(element);

      return {
        tagName: element.tagName.toLowerCase(),
        id: element.id || null,
        className: element.className || null,
        text: element.textContent?.trim().substring(0, 100) || null,
        value: element.value || null,
        href: element.href || null,
        src: element.src || null,
        isVisible: styles.display !== 'none' && styles.visibility !== 'hidden',
        isEnabled: !element.disabled,
        position: {
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height
        },
        attributes: Array.from(element.attributes).reduce((acc, attr) => {
          acc[attr.name] = attr.value;
          return acc;
        }, {})
      };
    },

    // Trigger event on element
    triggerEvent(element, eventType, options = {}) {
      const event = new Event(eventType, {
        bubbles: true,
        cancelable: true,
        ...options
      });
      element.dispatchEvent(event);
    }
  };

  // ============================================
  // MCP BROWSER CONTROL BORDER
  // ============================================

  /**
   * Show visual green border when tab is being controlled by MCP Browser
   */
  function showControlBorder() {
    if (!document.getElementById('mcp-browser-control-border')) {
      const border = document.createElement('div');
      border.id = 'mcp-browser-control-border';
      border.style.cssText = `
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        border: 4px solid #4CAF50;
        box-shadow: inset 0 0 10px rgba(76, 175, 80, 0.5);
        pointer-events: none;
        z-index: 2147483647;
        box-sizing: border-box;
      `;
      document.body.appendChild(border);
      console.log('[MCP Browser] Control border shown');
    }
  }

  /**
   * Hide visual border when tab is no longer controlled
   */
  function hideControlBorder() {
    const border = document.getElementById('mcp-browser-control-border');
    if (border) {
      border.remove();
      console.log('[MCP Browser] Control border hidden');
    }
  }

  // Listen for commands from background
  // Wrap in try-catch to handle extension context invalidation
  try {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    (async () => {
      try {
        switch (request.type) {
          case 'show_control_border':
            showControlBorder();
            sendResponse({ success: true });
            break;

          case 'hide_control_border':
            hideControlBorder();
            sendResponse({ success: true });
            break;

          case 'navigate':
            window.location.href = request.url;
            sendResponse({ success: true });
            break;

          case 'click':
            const clickElement = domHelpers.getElement(request.params);
            if (!clickElement) {
              sendResponse({ success: false, error: 'Element not found' });
              break;
            }

            clickElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            await new Promise(resolve => setTimeout(resolve, 500));
            clickElement.click();

            sendResponse({
              success: true,
              elementInfo: domHelpers.getElementInfo(clickElement)
            });
            break;

          case 'fill':
            const fillElement = domHelpers.getElement(request.params);
            if (!fillElement) {
              sendResponse({ success: false, error: 'Element not found' });
              break;
            }

            if (!['input', 'textarea', 'select'].includes(fillElement.tagName.toLowerCase())) {
              sendResponse({ success: false, error: 'Element is not a form field' });
              break;
            }

            fillElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            await new Promise(resolve => setTimeout(resolve, 300));

            if (fillElement.tagName.toLowerCase() === 'select') {
              fillElement.value = request.params.value;
              domHelpers.triggerEvent(fillElement, 'change');
            } else {
              fillElement.focus();
              fillElement.value = '';

              // Simulate typing for better compatibility
              for (const char of request.params.value) {
                fillElement.value += char;
                domHelpers.triggerEvent(fillElement, 'input');
                await new Promise(resolve => setTimeout(resolve, 20));
              }

              domHelpers.triggerEvent(fillElement, 'change');
              fillElement.blur();
            }

            sendResponse({
              success: true,
              elementInfo: domHelpers.getElementInfo(fillElement)
            });
            break;

          case 'submit':
            const formElement = domHelpers.getElement(request.params);
            if (!formElement) {
              sendResponse({ success: false, error: 'Form not found' });
              break;
            }

            const form = formElement.tagName.toLowerCase() === 'form'
              ? formElement
              : formElement.closest('form');

            if (!form) {
              sendResponse({ success: false, error: 'No form found for element' });
              break;
            }

            form.submit();
            sendResponse({ success: true });
            break;

          case 'get_element':
            const queryElement = domHelpers.getElement(request.params);
            const elementInfo = domHelpers.getElementInfo(queryElement);

            sendResponse({
              success: !!elementInfo,
              elementInfo,
              error: !elementInfo ? 'Element not found' : null
            });
            break;

          case 'get_elements':
            const { selector, limit = 10 } = request.params;
            const elements = Array.from(document.querySelectorAll(selector))
              .slice(0, limit)
              .map(el => domHelpers.getElementInfo(el));

            sendResponse({
              success: true,
              elements,
              count: elements.length
            });
            break;

          case 'wait_for_element':
            try {
              const element = await domHelpers.waitForElement(
                request.params.selector,
                request.params.timeout || 5000
              );

              sendResponse({
                success: true,
                elementInfo: domHelpers.getElementInfo(element)
              });
            } catch (error) {
              sendResponse({
                success: false,
                error: error.message
              });
            }
            break;

          case 'select_option':
            const selectElement = domHelpers.getElement(request.params);
            if (!selectElement || selectElement.tagName.toLowerCase() !== 'select') {
              sendResponse({ success: false, error: 'Select element not found' });
              break;
            }

            const optionValue = request.params.optionValue;
            const optionText = request.params.optionText;
            const optionIndex = request.params.optionIndex;

            let option;
            if (optionValue !== undefined) {
              option = selectElement.querySelector(`option[value="${optionValue}"]`);
            } else if (optionText !== undefined) {
              option = Array.from(selectElement.options).find(opt =>
                opt.textContent.trim() === optionText
              );
            } else if (optionIndex !== undefined) {
              option = selectElement.options[optionIndex];
            }

            if (!option) {
              sendResponse({ success: false, error: 'Option not found' });
              break;
            }

            selectElement.value = option.value;
            domHelpers.triggerEvent(selectElement, 'change');

            sendResponse({
              success: true,
              selectedValue: option.value,
              selectedText: option.textContent.trim()
            });
            break;

          case 'check_checkbox':
            const checkElement = domHelpers.getElement(request.params);
            if (!checkElement || checkElement.type !== 'checkbox') {
              sendResponse({ success: false, error: 'Checkbox not found' });
              break;
            }

            const shouldCheck = request.params.checked !== undefined
              ? request.params.checked
              : !checkElement.checked;

            if (checkElement.checked !== shouldCheck) {
              checkElement.click();
            }

            sendResponse({
              success: true,
              checked: checkElement.checked
            });
            break;

          case 'scroll_to':
            const scrollElement = request.params.selector
              ? domHelpers.getElement(request.params)
              : null;

            if (request.params.selector && !scrollElement) {
              sendResponse({ success: false, error: 'Element not found' });
              break;
            }

            if (scrollElement) {
              scrollElement.scrollIntoView({
                behavior: 'smooth',
                block: request.params.block || 'center'
              });
            } else {
              window.scrollTo({
                top: request.params.top || 0,
                left: request.params.left || 0,
                behavior: 'smooth'
              });
            }

            sendResponse({ success: true });
            break;

          case 'extractContent':
            try {
              // Check if Readability is available
              if (typeof Readability === 'undefined') {
                sendResponse({
                  success: false,
                  error: 'Readability library not loaded'
                });
                break;
              }

              // Clone the document to avoid modifying the actual page
              const documentClone = document.cloneNode(true);

              // Create a Readability object
              const reader = new Readability(documentClone, {
                // Options for better content extraction
                debug: false,
                maxElemsToParse: 0, // 0 means no limit
                nbTopCandidates: 5,
                charThreshold: 500,
                classesToPreserve: ['highlight', 'important', 'code']
              });

              // Parse the document
              const article = reader.parse();

              if (article) {
                // Extract additional metadata
                const metadata = {
                  url: window.location.href,
                  domain: window.location.hostname,
                  pathname: window.location.pathname,
                  timestamp: new Date().toISOString(),

                  // Try to get additional metadata from meta tags
                  author: article.byline ||
                    document.querySelector('meta[name="author"]')?.content ||
                    document.querySelector('meta[property="article:author"]')?.content ||
                    null,

                  publishDate:
                    document.querySelector('meta[property="article:published_time"]')?.content ||
                    document.querySelector('meta[name="publish_date"]')?.content ||
                    document.querySelector('time[datetime]')?.getAttribute('datetime') ||
                    null,

                  description:
                    document.querySelector('meta[name="description"]')?.content ||
                    document.querySelector('meta[property="og:description"]')?.content ||
                    null,

                  image:
                    document.querySelector('meta[property="og:image"]')?.content ||
                    document.querySelector('meta[name="twitter:image"]')?.content ||
                    null,

                  keywords:
                    document.querySelector('meta[name="keywords"]')?.content?.split(',').map(k => k.trim()) ||
                    [],

                  language: article.lang ||
                    document.documentElement.lang ||
                    document.querySelector('meta[property="og:locale"]')?.content ||
                    null
                };

                sendResponse({
                  success: true,
                  content: {
                    title: article.title || document.title,
                    textContent: article.textContent, // Clean text
                    excerpt: article.excerpt,
                    byline: article.byline,
                    length: article.length, // Estimated reading time in minutes
                    htmlContent: article.content, // HTML content
                    siteName: article.siteName,
                    metadata: metadata,
                    wordCount: article.textContent ? article.textContent.split(/\s+/).length : 0
                  }
                });
              } else {
                // Fallback for pages that Readability can't parse
                // Extract basic text content
                const textContent = document.body ? document.body.innerText : '';
                const title = document.title;

                sendResponse({
                  success: true,
                  content: {
                    title: title,
                    textContent: textContent,
                    excerpt: textContent.substring(0, 200) + '...',
                    byline: null,
                    length: Math.ceil(textContent.split(/\s+/).length / 200), // Rough estimate
                    htmlContent: null,
                    siteName: window.location.hostname,
                    metadata: {
                      url: window.location.href,
                      domain: window.location.hostname,
                      pathname: window.location.pathname,
                      timestamp: new Date().toISOString()
                    },
                    wordCount: textContent.split(/\s+/).length,
                    fallback: true // Indicate this is fallback extraction
                  }
                });
              }
            } catch (error) {
              console.error('[mcp-browser] Content extraction error:', error);
              sendResponse({
                success: false,
                error: error.message || 'Failed to extract content'
              });
            }
            break;

          default:
            sendResponse({ success: false, error: 'Unknown command type' });
        }
      } catch (error) {
        console.error('[mcp-browser] Command error:', error);
        sendResponse({
          success: false,
          error: error.message || 'Command execution failed'
        });
      }
    })();

    // Return true to indicate async response
    return true;
  });
  } catch (e) {
    // Extension context invalidated - ignore
    console.debug('[MCP Browser] Could not add message listener - context invalidated');
  }

  // Initial console message to confirm injection
  console.log('[mcp-browser] Console capture initialized');

  // Safe helper to get extension version
  function safeGetVersion() {
    try {
      return chrome.runtime.getManifest ? chrome.runtime.getManifest().version : '1.0.0';
    } catch (e) {
      return '1.0.0';
    }
  }

  // Safe helper to get extension id
  function safeGetId() {
    try {
      return chrome.runtime.id || 'unknown';
    } catch (e) {
      return 'unknown';
    }
  }

  // Extension detection helpers
  (function setupDetection() {
    try {
      // Inject detection marker
      const marker = document.createElement('div');
      marker.setAttribute('data-mcp-browser-extension', 'true');
      marker.dataset.version = safeGetVersion();
      marker.style.display = 'none';
      marker.id = 'mcp-browser-extension-marker';
      document.documentElement.appendChild(marker);

      // Add class to HTML element
      document.documentElement.classList.add('mcp-browser-extension-active');

      // Expose global flag
      window.__MCP_BROWSER_EXTENSION__ = {
        installed: true,
        version: safeGetVersion(),
        timestamp: Date.now()
      };

      // Listen for detection pings
      addTrackedListener(window, 'message', function(event) {
        if (event.data && event.data.type === 'MCP_BROWSER_PING') {
          // Respond with pong
          window.postMessage({
            type: 'MCP_BROWSER_PONG',
            status: 'connected',
            version: safeGetVersion(),
            id: safeGetId(),
            info: 'MCP Browser Extension Active'
          }, '*');
        }

        // Handle test requests
        if (event.data && event.data.type === 'MCP_BROWSER_TEST') {
          window.postMessage({
            type: 'MCP_BROWSER_TEST_RESPONSE',
            success: true,
            timestamp: Date.now()
          }, '*');
        }
      });

      // Dispatch ready event
      const readyEvent = new CustomEvent('mcp-browser-extension-ready', {
        detail: {
          version: safeGetVersion(),
          id: safeGetId()
        }
      });
      document.dispatchEvent(readyEvent);

      // Listen for test pings via custom events
      addTrackedListener(document, 'mcp-browser-test-ping', function(event) {
        const responseEvent = new CustomEvent('mcp-browser-test-pong', {
          detail: {
            timestamp: event.detail.timestamp,
            version: safeGetVersion()
          }
        });
        document.dispatchEvent(responseEvent);
      });
    } catch (e) {
      // Extension context invalidated - ignore
      console.debug('[MCP Browser] Detection setup failed - context invalidated');
    }
  })();

  // ============================================
  // KEEPALIVE PORT CONNECTION
  // ============================================

  let keepalivePort = null;
  let keepaliveReconnectAttempts = 0;
  const MAX_KEEPALIVE_RECONNECT_ATTEMPTS = 5;

  /**
   * Establish keepalive port connection to service worker
   */
  function connectKeepalivePort() {
    try {
      keepalivePort = chrome.runtime.connect({ name: 'keepalive' });
      keepaliveReconnectAttempts = 0;

      console.log('[MCP Browser Content] Keepalive port connected');

      keepalivePort.onMessage.addListener((message) => {
        if (message.type === 'keepalive_ack') {
          console.log('[MCP Browser Content] Keepalive acknowledged');
        }
      });

      keepalivePort.onDisconnect.addListener(() => {
        console.log('[MCP Browser Content] Keepalive port disconnected');
        keepalivePort = null;

        // Attempt reconnection with exponential backoff
        if (keepaliveReconnectAttempts < MAX_KEEPALIVE_RECONNECT_ATTEMPTS) {
          const delay = Math.min(1000 * Math.pow(2, keepaliveReconnectAttempts), 30000);
          keepaliveReconnectAttempts++;
          console.log(`[MCP Browser Content] Reconnecting keepalive in ${delay}ms (attempt ${keepaliveReconnectAttempts})`);
          setTimeout(connectKeepalivePort, delay);
        } else {
          console.warn('[MCP Browser Content] Max keepalive reconnect attempts reached');
        }
      });
    } catch (e) {
      // Check if context was invalidated - stop retrying
      if (e.message && e.message.includes('Extension context invalidated')) {
        console.debug('[MCP Browser Content] Extension context invalidated - stopping keepalive');
        return;
      }
      console.error('[MCP Browser Content] Failed to connect keepalive port:', e);
    }
  }

  // Initialize keepalive port on script load
  connectKeepalivePort();

})();