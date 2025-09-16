/*! GharFix Always-Visible Chatbot Widget v1.0.1 */
(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    API_BASE: 'https://gharfix-chatbot.onrender.com',
    API_ENDPOINT: '/chat',
    TITLE: '🏠 GharFix Assistant',
    SUBTITLE: 'Always here to help',
    STORAGE_KEY: 'gfc_conversation_id',
    MINIMIZED_KEY: 'gfc_minimized_state',
    WELCOME_MESSAGE: `Welcome to GharFix! I'm here 24/7 to help you with:

🔧 Plumbing & Electrical
🧹 Cleaning Services
👗 Tailoring Services
🍳 Chef Services
💆 Massage & Wellness
🏠 And much more!

What service do you need today?`,
    QUICK_ACTIONS: [
      { key: 'our_services', label: 'Our Services', message: 'List all the services' },
      { key: 'book_now',    label: 'Book Now',      message: 'I want to book a service' },
      { key: 'pricing',     label: 'Pricing',       message: 'What are your rates?' },
      { key: 'emergency',   label: 'Emergency',     message: 'I need emergency help' }
    ]
  };

  // State
  let conversationId = getOrCreateConversationId();
  let isTyping       = false;
  let isMinimized    = localStorage.getItem(CONFIG.MINIMIZED_KEY) === 'true';
  let elements       = {};

  // Helpers
  function getOrCreateConversationId() {
    let id = localStorage.getItem(CONFIG.STORAGE_KEY);
    if (!id) {
      id = 'cid-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
      localStorage.setItem(CONFIG.STORAGE_KEY, id);
    }
    return id;
  }

  function createEl(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'className') el.className = v;
      else el.setAttribute(k, v);
    });
    (Array.isArray(children) ? children : [children]).forEach(c => {
      if (!c) return;
      if (typeof c === 'string') el.appendChild(document.createTextNode(c));
      else el.appendChild(c);
    });
    return el;
  }

  // Build widget DOM
  function buildWidget() {
    // Minimize button
    const minBtn = createEl('button', {
      id:    'gfc-minimize',
      type:  'button',
      title: isMinimized ? 'Expand chat' : 'Minimize chat'
    }, [ isMinimized ? '+' : '−' ]);

    // Header
    const header = createEl('div', { id: 'gfc-header' }, [
      createEl('h3', {}, [CONFIG.TITLE]),
      createEl('p', {}, [CONFIG.SUBTITLE]),
      minBtn
    ]);

    // Messages
    const messages = createEl('div', { id: 'gfc-messages' });

    // Quick actions
    const qa = createEl('div', { className: 'gfc-quick-actions' });
    CONFIG.QUICK_ACTIONS.forEach(action => {
      const btn = createEl('button', {
        className: 'gfc-quick-btn',
        type:      'button',
        'data-key': action.key
      }, [action.label]);
      btn.addEventListener('click', () => handleQuick(action));
      qa.appendChild(btn);
    });

    // Input area
    const input     = createEl('input', { id: 'gfc-input', type: 'text', placeholder: 'Type your message...', autocomplete: 'off' });
    const sendBtn   = createEl('button', { id: 'gfc-send', type: 'submit' }, ['Send']);
    const inputBar  = createEl('form', { id: 'gfc-inputbar', autocomplete: 'off' }, [input, sendBtn]);

    // Container
    const container = createEl('div', {
      id:        'gfc-always-chat',
      className: isMinimized ? 'minimized' : ''
    }, [header, messages, qa, inputBar]);

    return { container, header, messages, input, sendBtn, minBtn, inputBar };
  }

  // Message utilities
  function addMessage(text, sender) {
    const bubble = createEl('div', { className: 'gfc-bubble' });
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    const msg = createEl('div', { className: `gfc-msg gfc-${sender}` }, [bubble]);
    elements.messages.appendChild(msg);
    elements.messages.scrollTop = elements.messages.scrollHeight;
  }

  function showTyping() {
    const dots = [1,2,3].map(() => createEl('span', { className: 'dot' }));
    const typing = createEl('div', { className: 'gfc-typing' }, ['Assistant is typing', ...dots]);
    const bubble = createEl('div', { className: 'gfc-bubble' }, [typing]);
    const row = createEl('div', { className: 'gfc-msg gfc-bot', id: 'gfc-typing' }, [bubble]);
    elements.messages.appendChild(row);
    elements.messages.scrollTop = elements.messages.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('gfc-typing');
    if (el) el.remove();
  }

  // API call
  async function sendMessage(text) {
    if (isTyping) return;
    isTyping       = true;
    elements.sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch(CONFIG.API_BASE + CONFIG.API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, conversation_id: conversationId })
      });
      hideTyping();
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      addMessage(data.response || 'Sorry, cannot process your request.', 'bot');
    } catch (err) {
      hideTyping();
      console.error(err);
      addMessage('Network error. Please try again later.', 'bot');
    } finally {
      isTyping       = false;
      elements.sendBtn.disabled = false;
    }
  }

  // Event handlers
  function toggleMinimize() {
    isMinimized = !isMinimized;
    localStorage.setItem(CONFIG.MINIMIZED_KEY, isMinimized);
    elements.container.classList.toggle('minimized', isMinimized);
    elements.minBtn.textContent = isMinimized ? '+' : '−';
    elements.minBtn.title = isMinimized ? 'Expand chat' : 'Minimize chat';
    if (!isMinimized) elements.input.focus();
  }

  function handleQuick(action) {
    if (isMinimized) toggleMinimize();
    addMessage(action.message, 'user');
    sendMessage(action.message);
  }

  function handleSubmit(evt) {
    evt.preventDefault();
    if (isMinimized) {
      toggleMinimize();
      return;
    }
    const msg = elements.input.value.trim();
    if (!msg) return;
    addMessage(msg, 'user');
    elements.input.value = '';
    sendMessage(msg);
  }

  function handleContainerClick(evt) {
    // If minimized and clicking anywhere on container (excluding input)
    if (isMinimized && evt.target === elements.container) {
      toggleMinimize();
    }
  }

  // Initialization
  function init() {
    elements = buildWidget();
    document.body.appendChild(elements.container);

    // Listeners
    elements.minBtn.addEventListener('click', toggleMinimize);
    elements.inputBar.addEventListener('submit', handleSubmit);
    elements.container.addEventListener('click', handleContainerClick);

    // Show welcome if expanded
    setTimeout(() => {
  // Always show welcome message when widget first loads
  if (elements.messages.children.length === 0) {
    addMessage(CONFIG.WELCOME_MESSAGE, 'bot');
  }
}, 500);
    elements.minBtn.textContent = isMinimized ? '+' : '−';
    elements.minBtn.title = isMinimized ? 'Expand chat' : 'Minimize chat';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose API
  window.GharFixAlwaysWidget = {
    expand: () => { if (isMinimized) toggleMinimize(); },
    minimize: () => { if (!isMinimized) toggleMinimize(); },
    toggle: toggleMinimize
  };

})();
