// Avito Messenger Frontend Application

let currentChatId = null;
let chats = [];
let messages = [];

// DOM Elements
const chatsList = document.getElementById('chatsList');
const messagesList = document.getElementById('messagesList');
const messagesHeader = document.getElementById('messagesHeader');
const replyForm = document.getElementById('replyForm');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const refreshBtn = document.getElementById('refreshBtn');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadChats();
    setupEventListeners();
});

function setupEventListeners() {
    refreshBtn.addEventListener('click', () => {
        loadChats();
        if (currentChatId) {
            loadMessages(currentChatId);
        }
    });

    sendBtn.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

async function loadChats() {
    showLoading();
    try {
        const response = await fetch('/api/chats');
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        chats = data.chats || [];
        
        // Отладочное логирование в консоль браузера
        if (chats.length > 0) {
            console.log('First chat structure:', chats[0]);
            console.log('First chat title:', chats[0].title);
            console.log('First chat context:', chats[0].context);
        }
        
        renderChats();
    } catch (error) {
        showError('Ошибка загрузки чатов: ' + error.message);
    } finally {
        hideLoading();
    }
}

function renderChats() {
    if (chats.length === 0) {
        chatsList.innerHTML = '<div class="loading">Нет активных чатов</div>';
        return;
    }
    
    chatsList.innerHTML = chats.map(chat => {
        const lastMessage = chat.last_message || {};
        const time = lastMessage.created 
            ? formatTime(lastMessage.created * 1000)
            : '';
        
        // Правильно извлекаем текст последнего сообщения
        let preview = 'Нет сообщений';
        if (lastMessage.content) {
            if (typeof lastMessage.content === 'object' && lastMessage.content.text) {
                preview = lastMessage.content.text;
            } else if (typeof lastMessage.content === 'string') {
                preview = lastMessage.content;
            }
        } else if (lastMessage.text) {
            preview = lastMessage.text;
        }
        
        // Получаем имя пользователя (основное название чата)
        let userName = 'Пользователь';
        if (chat.users && chat.users.length > 0 && chat.users[0].name) {
            userName = chat.users[0].name;
        } else if (chat.user_id) {
            userName = `ID ${chat.user_id}`;
        }
        
        // Получаем название объявления (подзаголовок)
        let itemTitle = '';
        if (chat.context && chat.context.value && chat.context.value.title) {
            itemTitle = chat.context.value.title;
        }
        
        return `
            <div class="chat-item ${chat.id === currentChatId ? 'active' : ''}" 
                 onclick="selectChat('${chat.id}')">
                <div class="chat-item-header">
                    <div class="chat-item-name">${escapeHtml(userName)}</div>
                    <div class="chat-item-time">${time}</div>
                </div>
                ${itemTitle ? `<div class="chat-item-subtitle">${escapeHtml(itemTitle)}</div>` : ''}
                <div class="chat-item-preview">${escapeHtml(preview)}</div>
            </div>
        `;
    }).join('');
}

async function selectChat(chatId) {
    currentChatId = chatId;
    renderChats();
    await loadMessages(chatId);
    replyForm.style.display = 'block';
}

async function loadMessages(chatId) {
    showLoading();
    try {
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        messages = data.messages || [];
        
        // Получаем информацию о чате
        const chat = chats.find(c => c.id === chatId);
        let userName = 'Пользователь';
        let itemTitle = '';
        
        if (chat) {
            // Получаем имя пользователя (основное название)
            if (chat.users && chat.users.length > 0 && chat.users[0].name) {
                userName = chat.users[0].name;
            } else if (chat.user_id) {
                userName = `ID ${chat.user_id}`;
            }
            
            // Получаем название объявления (подзаголовок)
            if (chat.context && chat.context.value && chat.context.value.title) {
                itemTitle = chat.context.value.title;
            }
        }
        
        // Формируем заголовок с именем пользователя и названием объявления
        messagesHeader.innerHTML = `
            <h2>${escapeHtml(userName)}</h2>
            ${itemTitle ? `<div class="chat-subtitle">${escapeHtml(itemTitle)}</div>` : ''}
        `;
        
        renderMessages();
    } catch (error) {
        showError('Ошибка загрузки сообщений: ' + error.message);
    } finally {
        hideLoading();
    }
}

function renderMessages() {
    if (messages.length === 0) {
        messagesList.innerHTML = `
            <div class="empty-state">
                <p>Нет сообщений в этом чате</p>
            </div>
        `;
        return;
    }
    
    messagesList.innerHTML = messages.map(msg => {
        const isOwn = msg.type === 'outgoing' || msg.direction === 'out';
        const time = msg.created 
            ? formatTime(msg.created * 1000)
            : '';
        const author = msg.author_id || msg.author || msg.user_id || 'Пользователь';
        
        // Правильно извлекаем текст из структуры Avito API
        let text = '';
        if (msg.content && msg.content.text) {
            text = msg.content.text;
        } else if (typeof msg.content === 'string') {
            text = msg.content;
        } else if (msg.text) {
            text = msg.text;
        } else {
            text = '[Сообщение без текста]';
        }
        
        return `
            <div class="message-item ${isOwn ? 'own' : ''}">
                <div class="message-item-header">
                    <div class="message-item-author">${escapeHtml(String(author))}</div>
                    <div class="message-item-time">${time}</div>
                </div>
                <div class="message-item-text">${escapeHtml(text)}</div>
            </div>
        `;
    }).join('');
    
    // Прокрутка вниз
    messagesList.scrollTop = messagesList.scrollHeight;
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || !currentChatId) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch('/api/messages/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: currentChatId,
                message: text
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Очищаем поле ввода
        messageInput.value = '';
        
        // Обновляем сообщения
        await loadMessages(currentChatId);
        
        // Обновляем список чатов
        await loadChats();
    } catch (error) {
        showError('Ошибка отправки сообщения: ' + error.message);
    } finally {
        hideLoading();
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // Если сегодня
    if (diff < 24 * 60 * 60 * 1000 && date.getDate() === now.getDate()) {
        return date.toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    // Если вчера
    if (diff < 48 * 60 * 60 * 1000) {
        return 'Вчера ' + date.toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    // Иначе полная дата
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading() {
    loadingOverlay.classList.add('active');
}

function hideLoading() {
    loadingOverlay.classList.remove('active');
}

function showError(message) {
    alert('Ошибка: ' + message);
    console.error(message);
}



