import './style.css';
const AGENT_URL = import.meta.env.VITE_AGENT_URL || 'http://localhost:5000';

const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const resetButton = document.getElementById('resetButton');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

const instancePanel = document.getElementById('instancePanel');
const instanceIdSpan = document.getElementById('instanceId');
const instanceStatusSpan = document.getElementById('instanceStatus');

// Auth Elements
const authOverlay = document.getElementById('authOverlay');
const authForm = document.getElementById('authForm');
const authSubmit = document.getElementById('authSubmit');
const authError = document.getElementById('authError');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');

const logoutButton = document.getElementById('logoutButton');

let isProcessing = false;
let currentAuthMode = 'login';
let authToken = localStorage.getItem('authToken');
let currentUser = localStorage.getItem('currentUser');

// Auth Functions
function switchAuth(mode) {
    currentAuthMode = mode;
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.classList.toggle('active', tab.textContent.toLowerCase() === mode);
    });
    authSubmit.textContent = mode === 'login' ? 'Login' : 'Register';
    authError.textContent = '';
}

// Expose to window for HTML onclick
window.switchAuth = switchAuth;

function updateAuthUI() {
    if (authToken) {
        authOverlay.classList.add('hidden');
        logoutButton.style.display = 'block';
        updateInstanceInfo(); // Fetch info on login
        loadChatHistory(); // Load history on login
    } else {
        authOverlay.classList.remove('hidden');
        logoutButton.style.display = 'none';
        instancePanel.style.display = 'none';
    }
}

// Check Auth on Load
updateAuthUI();

// Handle Auth Submit
authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = usernameInput.value;
    const password = passwordInput.value;
    
    try {
        const endpoint = currentAuthMode === 'login' ? '/login' : '/register';
        const response = await fetch(`${AGENT_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Auth failed');
        }
        
        if (currentAuthMode === 'register') {
            // Auto login after register or ask to login? 
            // Let's switch to login mode for simplicity or just auto-login if the API returned a token (it currently doesn't for register)
            // My API implementation for register returns {message, user_id}, not token.
            // So we switch to login.
            switchAuth('login');
            authError.style.color = 'var(--success)';
            authError.textContent = 'Registration successful! Please login.';
            return;
        }
        
        // Login success
        authToken = data.token;
        currentUser = data.username;
        localStorage.setItem('authToken', authToken);
        localStorage.setItem('currentUser', currentUser);
        
        updateAuthUI();
        
        // Load history? (Not implemented in API yet, but we could)
        
    } catch (error) {
        authError.style.color = 'var(--error)';
        authError.textContent = error.message;
    }
});

// Logout helper
function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    authToken = null;
    currentUser = null;
    authToken = null;
    currentUser = null;
    updateAuthUI();
}

// Expose to window for HTML onclick
window.logout = logout;

// Check agent health on load
// Check agent health on load
async function checkHealth() {
    try {
        const response = await fetch(`${AGENT_URL}/health`);
        
        if (!response.ok) {
            statusDot.className = 'status-dot error';
            statusText.textContent = `Error: ${response.status}`;
            return;
        }

        const data = await response.json();
        
        if (data.status === 'healthy' && data.orchestrator_connected) {
            statusDot.className = 'status-dot connected';
            let statusMsg = 'Connected';
            
            if (authToken) {
                await updateInstanceInfo();
                const instanceId = instanceIdSpan.textContent;
                if (instanceId && instanceId !== 'Unknown') {
                    statusMsg += ` ${instanceId}`;
                }
            }
            statusText.textContent = statusMsg;
        } else {
            statusDot.className = 'status-dot error';
            statusText.textContent = 'Disconnected';
        }
    } catch (error) {
        statusDot.className = 'status-dot error';
        statusText.textContent = 'Agent offline';
    }
}

// Load Chat History
async function loadChatHistory() {
    if (!authToken) return;
    
    try {
        const response = await fetch(`${AGENT_URL}/chat/history`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            // Clear existing messages except welcome
            messagesContainer.innerHTML = `
                <div class="message assistant">
                    <div class="message-content">
                        <p>👋 Hello! I'm your Blender AI assistant. I can help you create 3D scenes!</p>
                        <p>Try asking me to:</p>
                        <ul>
                            <li>"Create a red cube"</li>
                            <li>"Add a blue sphere next to it"</li>
                            <li>"Render the scene"</li>
                        </ul>
                    </div>
                </div>
            `;
            
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    if (msg.role === 'user') {
                        addMessage(msg.content, true);
                    } else if (msg.role === 'assistant') {
                        addMessage(msg.content, false, msg.tool_calls);
                    }
                });
            }
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// Update Instance Info
async function updateInstanceInfo() {
    if (!authToken) return;
    
    try {
        const response = await fetch(`${AGENT_URL}/instance`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            instancePanel.style.display = 'block';
            instanceIdSpan.textContent = data.instance_id || 'Unknown';
            
            // Capitalize status
            const status = (data.status || 'Unknown').charAt(0).toUpperCase() + (data.status || 'Unknown').slice(1);
            instanceStatusSpan.textContent = status;
            
            // Color code status
            if (data.status === 'running') {
                instanceStatusSpan.style.color = '#4caf50';
            } else {
                instanceStatusSpan.style.color = '#ff9800';
            }
        }
    } catch (error) {
        console.error('Failed to fetch instance info:', error);
    }
}

// Add message to chat
function addMessage(content, isUser = false, toolCalls = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Add main message
    const textP = document.createElement('p');
    textP.textContent = content;
    contentDiv.appendChild(textP);
    
    // Add tool calls if any
    if (toolCalls && toolCalls.length > 0) {
        toolCalls.forEach(toolCall => {
            const toolDiv = document.createElement('div');
            toolDiv.className = 'tool-call';
            
            const toolName = document.createElement('div');
            toolName.className = 'tool-call-name';
            toolName.textContent = `🔧 ${toolCall.tool}`;
            toolDiv.appendChild(toolName);
            
            // Show result
            if (toolCall.result) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'tool-call-result';
                
                // Check if there's a rendered image
                if (toolCall.result.image_base64) {
                    const img = document.createElement('img');
                    img.className = 'render-image';
                    img.src = `data:image/png;base64,${toolCall.result.image_base64}`;
                    img.alt = 'Rendered scene';
                    contentDiv.appendChild(img);
                } else {
                    resultDiv.textContent = JSON.stringify(toolCall.result, null, 2);
                    toolDiv.appendChild(resultDiv);
                }
            }
            
            contentDiv.appendChild(toolDiv);
        });
    }
    
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return { messageDiv, contentDiv, textP };
}

// Show typing indicator
function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typing-indicator';
    
    const typingContent = document.createElement('div');
    typingContent.className = 'typing-indicator';
    
    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('div');
        dot.className = 'typing-dot';
        typingContent.appendChild(dot);
    }
    
    typingDiv.appendChild(typingContent);
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Remove typing indicator
function hideTyping() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Send message
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isProcessing) return;
    
    // Add user message
    addMessage(message, true);
    messageInput.value = '';
    
    // Disable input
    isProcessing = true;
    sendButton.disabled = true;
    messageInput.disabled = true;
    
    // Create empty assistant message
    const { contentDiv, textP } = addMessage('', false);
    
    try {
        const response = await fetch(`${AGENT_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ message })
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep the last incomplete chunk
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    if (dataStr === '[DONE]') continue;
                    
                    try {
                        const data = JSON.parse(dataStr);
                        
                        if (data.content) {
                            textP.textContent += data.content;
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }
                        
                        if (data.status === 'executing_tools') {
                            const statusDiv = document.createElement('div');
                            statusDiv.className = 'tool-status';
                            statusDiv.textContent = `⚙️ Executing ${data.count} tool(s)...`;
                            statusDiv.style.fontStyle = 'italic';
                            statusDiv.style.color = '#888';
                            statusDiv.style.marginTop = '8px';
                            contentDiv.appendChild(statusDiv);
                        }
                        
                        if (data.tool_call) {
                            const toolCall = data.tool_call;
                            const toolDiv = document.createElement('div');
                            toolDiv.className = 'tool-call';
                            
                            const toolName = document.createElement('div');
                            toolName.className = 'tool-call-name';
                            toolName.textContent = `🔧 ${toolCall.tool}`;
                            toolDiv.appendChild(toolName);
                            
                            if (toolCall.result) {
                                const resultDiv = document.createElement('div');
                                resultDiv.className = 'tool-call-result';
                                
                                if (toolCall.result.image_base64) {
                                    const img = document.createElement('img');
                                    img.className = 'render-image';
                                    img.src = `data:image/png;base64,${toolCall.result.image_base64}`;
                                    img.alt = 'Rendered scene';
                                    contentDiv.appendChild(img);
                                } else {
                                    resultDiv.textContent = JSON.stringify(toolCall.result, null, 2);
                                    toolDiv.appendChild(resultDiv);
                                }
                            }
                            
                            contentDiv.appendChild(toolDiv);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                            
                            // Remove executing status if present
                            const statusDiv = contentDiv.querySelector('.tool-status');
                            if (statusDiv) statusDiv.remove();
                        }
                        
                        if (data.error) {
                            textP.textContent += `\n[Error: ${data.error}]`;
                        }
                        
                    } catch (e) {
                        console.error('Error parsing SSE:', e);
                    }
                }
            }
        }
        
        // Update instance info after chat
        updateInstanceInfo();
        
    } catch (error) {
        textP.textContent += `\n[Error: ${error.message}]`;
    } finally {
        isProcessing = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// Reset conversation
async function resetConversation() {
    if (!confirm('Reset the conversation? This will clear all messages.')) {
        return;
    }
    
    try {
        const response = await fetch(`${AGENT_URL}/reset`, { 
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        // Clear messages except welcome
        messagesContainer.innerHTML = `
            <div class="message assistant">
                <div class="message-content">
                    <p>👋 Hello! I'm your Blender AI assistant. I can help you create 3D scenes!</p>
                    <p>Try asking me to:</p>
                    <ul>
                        <li>"Create a red cube"</li>
                        <li>"Add a blue sphere next to it"</li>
                        <li>"Render the scene"</li>
                    </ul>
                </div>
            </div>
        `;
    } catch (error) {
        alert('Failed to reset conversation');
    }
}

// Event listeners
sendButton.addEventListener('click', sendMessage);
resetButton.addEventListener('click', resetConversation);

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Check health on load and periodically
checkHealth();
setInterval(() => {
    checkHealth();
}, 10000); // Every 10 seconds
