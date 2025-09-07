class GharFixChatbot {
    constructor() {
        this.apiUrl = '/chat'; // Use relative URL for deployed version
        this.conversationId = 'conv_' + Date.now();
        this.isTyping = false;
        
        this.initializeElements();
        this.bindEvents();
        this.showWelcomeMessage();
    }
    
    initializeElements() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.quickButtons = document.querySelectorAll('.quick-btn');
    }
    
    bindEvents() {
        this.sendButton.addEventListener('click', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.quickButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.getAttribute('data-msg');
                this.messageInput.value = message;
                this.sendMessage();
            });
        });
    }
    
    showWelcomeMessage() {
        const welcomeMsg = "👋 Hi! I'm your GharFix Assistant. I can help you with:\n\n• Service information and booking\n• Pricing and packages\n• Emergency services\n• General inquiries\n\nWhat would you like to know?";
        this.addMessage(welcomeMsg, 'bot');
    }
    
    addMessage(content, sender, isTyping = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        if (isTyping) {
            messageDiv.innerHTML = `
                <div class="typing">
                    <span>Assistant is typing</span>
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `<div class="message-content">${content.replace(/\n/g, '<br>')}</div>`;
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        
        return messageDiv;
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        
        // Show typing indicator
        this.isTyping = true;
        this.sendButton.disabled = true;
        const typingIndicator = this.addMessage('', 'bot', true);
        
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Remove typing indicator
            typingIndicator.remove();
            
            // Add bot response
            if (data.response) {
                this.addMessage(data.response, 'bot');
            } else {
                this.addMessage('Sorry, I couldn\'t process your request. Please try again.', 'bot');
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            typingIndicator.remove();
            
            let errorMessage = 'Sorry, I\'m having trouble connecting. Please try refreshing the page or contact support at +91 75068 55407.';
            this.addMessage(errorMessage, 'bot');
        } finally {
            this.isTyping = false;
            this.sendButton.disabled = false;
            this.messageInput.focus();
        }
    }
}

// Initialize chatbot when page loads
document.addEventListener('DOMContentLoaded', () => {
    new GharFixChatbot();
});
