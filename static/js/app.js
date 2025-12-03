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

// Глобальная переменная для ID текущего пользователя
let currentUserId = null;

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
        currentUserId = data.current_user_id; // Сохраняем ID текущего пользователя
        
        // Отладочное логирование в консоль браузера
        console.log('Current user ID:', currentUserId);
        if (chats.length > 0) {
            console.log('First chat structure:', chats[0]);
            console.log('First chat users:', chats[0].users);
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
        // Ищем пользователя, который НЕ является текущим (собеседника)
        let userName = 'Пользователь';
        let userAvatar = '';
        let otherUser = null;
        
        if (chat.users && chat.users.length > 0) {
            // Ищем собеседника (не текущего пользователя)
            otherUser = chat.users.find(u => u.id !== currentUserId);
            
            // Если не нашли, берем первого пользователя
            if (!otherUser) {
                otherUser = chat.users[0];
            }
            
            if (otherUser) {
                userName = otherUser.name || `ID ${otherUser.id}`;
                // Извлекаем аватарку из правильной структуры
                if (otherUser.avatar) {
                    if (otherUser.avatar.images && otherUser.avatar.images['48x48']) {
                        userAvatar = otherUser.avatar.images['48x48'];
                    } else if (otherUser.avatar.default) {
                        userAvatar = otherUser.avatar.default;
                    }
                }
                // Отладочное логирование
                if (chat.id === chats[0].id) {
                    console.log('First chat - other user:', otherUser);
                    console.log('First chat - avatar URL:', userAvatar);
                }
            }
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
                ${userAvatar ? `<img src="${escapeHtml(userAvatar)}" alt="${escapeHtml(userName)}" class="chat-item-avatar" onerror="this.style.display='none'">` : '<div class="chat-item-avatar-placeholder"></div>'}
                <div class="chat-item-content">
                    <div class="chat-item-header">
                        <div class="chat-item-name">${escapeHtml(userName)}</div>
                        <div class="chat-item-time">${time}</div>
                    </div>
                    ${itemTitle ? `<div class="chat-item-subtitle">${escapeHtml(itemTitle)}</div>` : ''}
                    <div class="chat-item-preview">${escapeHtml(preview)}</div>
                </div>
            </div>
        `;
    }).join('');
}

async function selectChat(chatId) {
    currentChatId = chatId;
    renderChats();
    await loadMessages(chatId);
    replyForm.style.display = 'block';
    
    // Помечаем чат прочитанным
    markChatAsRead(chatId);
}

async function markChatAsRead(chatId) {
    try {
        await fetch(`/api/chats/${chatId}/read`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Error marking chat as read:', error);
    }
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
        
        // Сохраняем информацию о чате и текущем пользователе
        window.currentChatInfo = data.chat_info;
        window.currentUserId = data.current_user_id;
        
        // Получаем информацию о чате
        const chat = chats.find(c => c.id === chatId) || data.chat_info;
        let userName = 'Пользователь';
        let userAvatar = '';
        let itemTitle = '';
        
        if (chat) {
            // Получаем имя пользователя (основное название)
            // Ищем пользователя, который НЕ является текущим (собеседника)
            let otherUser = null;
            
            if (chat.users && chat.users.length > 0) {
                // Ищем собеседника (не текущего пользователя)
                otherUser = chat.users.find(u => u.id !== currentUserId && u.id !== window.currentUserId);
                
                // Если не нашли, берем первого пользователя
                if (!otherUser) {
                    otherUser = chat.users[0];
                }
                
                if (otherUser) {
                    userName = otherUser.name || `ID ${otherUser.id}`;
                    // Извлекаем аватарку из правильной структуры
                    if (otherUser.avatar) {
                        if (otherUser.avatar.images && otherUser.avatar.images['48x48']) {
                            userAvatar = otherUser.avatar.images['48x48'];
                        } else if (otherUser.avatar.default) {
                            userAvatar = otherUser.avatar.default;
                        }
                    }
                }
            } else if (chat.user_id) {
                userName = `ID ${chat.user_id}`;
            }
            
            // Получаем название объявления (подзаголовок)
            if (chat.context && chat.context.value && chat.context.value.title) {
                itemTitle = chat.context.value.title;
            }
        }
        
        // Формируем заголовок с аватаркой, именем пользователя и названием объявления
        messagesHeader.innerHTML = `
            <div class="chat-header-wrapper">
                ${userAvatar ? `<img src="${escapeHtml(userAvatar)}" alt="${escapeHtml(userName)}" class="chat-avatar" onerror="this.style.display='none'">` : ''}
                <div class="chat-header-text">
                    <h2>${escapeHtml(userName)}</h2>
                    ${itemTitle ? `<div class="chat-subtitle">${escapeHtml(itemTitle)}</div>` : ''}
                </div>
            </div>
        `;
        
        // Показываем кнопку блокировки и привязываем её к пользователю
        const blockBtn = document.getElementById('blockUserBtn');
        if (blockBtn && chat && chat.users && chat.users.length > 0) {
            const otherUser = chat.users.find(u => u.id !== currentUserId && u.id !== window.currentUserId);
            if (otherUser) {
                blockBtn.style.display = 'inline-flex';
                blockBtn.onclick = () => blockUser(otherUser.id);
            }
        }
        
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
        
        // Получаем информацию об авторе сообщения
        let authorName = 'Пользователь';
        let authorAvatar = '';
        
        if (window.currentChatInfo && window.currentChatInfo.users) {
            const author = window.currentChatInfo.users.find(u => u.id === msg.author_id);
            if (author) {
                authorName = author.name || `ID ${msg.author_id}`;
                // Извлекаем аватарку из правильной структуры
                if (author.avatar) {
                    if (author.avatar.images && author.avatar.images['36x36']) {
                        authorAvatar = author.avatar.images['36x36'];
                    } else if (author.avatar.default) {
                        authorAvatar = author.avatar.default;
                    }
                }
            } else if (msg.author_id === window.currentUserId) {
                // Это наше сообщение
                authorName = 'Вы';
            }
        }
        
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
        
        // Проверяем можно ли удалить сообщение (только свои, не старше часа)
        const canDelete = isOwn && (Date.now() - msg.created * 1000) < 3600000;
        
        return `
            <div class="message-item ${isOwn ? 'own' : ''}" data-message-id="${msg.id}">
                ${!isOwn && authorAvatar ? `<img src="${escapeHtml(authorAvatar)}" alt="${escapeHtml(authorName)}" class="message-avatar" onerror="this.style.display='none'">` : ''}
                <div class="message-content">
                    <div class="message-item-header">
                        <div class="message-item-author">${escapeHtml(authorName)}</div>
                        <div class="message-item-time">${time}</div>
                        ${canDelete ? `<button class="btn-delete-message" onclick="deleteMessage('${msg.id}')" title="Удалить">🗑️</button>` : ''}
                    </div>
                    <div class="message-item-text">${escapeHtml(text)}</div>
                </div>
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

async function deleteMessage(messageId) {
    if (!confirm('Вы уверены, что хотите удалить это сообщение?')) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch('/api/messages/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chat_id: currentChatId,
                message_id: messageId
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Обновляем сообщения
        await loadMessages(currentChatId);
    } catch (error) {
        showError('Ошибка удаления сообщения: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function sendImage() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        showLoading();
        try {
            // Загружаем изображение
            const formData = new FormData();
            formData.append('image', file);
            
            const uploadResponse = await fetch('/api/images/upload', {
                method: 'POST',
                body: formData
            });
            
            const uploadData = await uploadResponse.json();
            
            if (uploadData.error) {
                showError(uploadData.error);
                return;
            }
            
            // Получаем ID загруженного изображения
            const imageData = uploadData.data;
            const imageId = Object.keys(imageData)[0];
            
            if (!imageId) {
                showError('Не удалось получить ID изображения');
                return;
            }
            
            // Отправляем сообщение с изображением
            const sendResponse = await fetch('/api/messages/send-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    chat_id: currentChatId,
                    image_id: imageId
                })
            });
            
            const sendData = await sendResponse.json();
            
            if (sendData.error) {
                showError(sendData.error);
                return;
            }
            
            // Обновляем сообщения
            await loadMessages(currentChatId);
            await loadChats();
        } catch (error) {
            showError('Ошибка отправки изображения: ' + error.message);
        } finally {
            hideLoading();
        }
    };
    
    input.click();
}

async function blockUser(userId) {
    if (!confirm('Вы уверены, что хотите заблокировать этого пользователя?')) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch('/api/blacklist/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                users: [{ id: userId }]
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        alert('Пользователь заблокирован');
        await loadChats();
    } catch (error) {
        showError('Ошибка блокировки пользователя: ' + error.message);
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



