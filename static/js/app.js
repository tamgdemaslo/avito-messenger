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
const scrollToBottomBtn = document.getElementById('scrollToBottomBtn');

// Глобальная переменная для ID текущего пользователя
let currentUserId = null;

// Автообновление и уведомления
let autoRefreshInterval = null;
let lastMessageCount = {};
let notificationSound = null;

// Создаем звук уведомления
function initNotificationSound() {
    // Используем Web Audio API для создания простого звука
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    notificationSound = () => {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    };
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNotificationSound();
    loadChats();
    setupEventListeners();
    checkTelegramStatus();
    startAutoRefresh();
});

function startAutoRefresh() {
    // Обновляем чаты каждые 5 секунд
    autoRefreshInterval = setInterval(async () => {
        await loadChats(true); // true = тихое обновление (без показа загрузки)
        
        // Если открыт чат, обновляем и его сообщения
        if (currentChatId) {
            await loadMessages(currentChatId, true);
        }
    }, 5000); // 5 секунд
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

async function checkTelegramStatus() {
    try {
        const response = await fetch('/api/telegram/status');
        const data = await response.json();
        
        if (!data.authorized) {
            // Показываем уведомление, если Telegram не авторизован
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #0088cc;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 14px;
                max-width: 400px;
            `;
            notification.innerHTML = `
                <span>📱 Telegram не подключен</span>
                <a href="/telegram/auth" style="color: white; text-decoration: underline; font-weight: 600;">Авторизоваться</a>
                <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 18px; margin-left: auto;">×</button>
            `;
            document.body.appendChild(notification);
            
            // Автоматически скрываем через 10 секунд
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 10000);
        }
    } catch (error) {
        console.log('Telegram status check failed:', error);
    }
}

function setupEventListeners() {
    refreshBtn.addEventListener('click', () => {
        loadChats();
        if (currentChatId) {
            loadMessages(currentChatId);
        }
    });

    sendBtn.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Кнопка прокрутки вниз
    if (scrollToBottomBtn) {
        scrollToBottomBtn.addEventListener('click', () => {
            messagesList.scrollTo({
                top: messagesList.scrollHeight,
                behavior: 'smooth'
            });
        });
    }
    
    // Показываем/скрываем кнопку прокрутки вниз при скролле
    if (messagesList) {
        messagesList.addEventListener('scroll', () => {
            const isAtBottom = messagesList.scrollHeight - messagesList.scrollTop - messagesList.clientHeight < 100;
            if (scrollToBottomBtn) {
                scrollToBottomBtn.style.display = isAtBottom ? 'none' : 'flex';
            }
        });
    }
}

async function loadChats(silent = false) {
    if (!silent) {
        showLoading();
    }
    
    try {
        const response = await fetch('/api/chats');
        const data = await response.json();
        
        if (data.error) {
            if (!silent) showError(data.error);
            return;
        }
        
        const newChats = data.chats || [];
        const oldChats = [...chats];
        
        // Проверяем новые сообщения
        let hasNewMessages = false;
        newChats.forEach(newChat => {
            const oldChat = oldChats.find(c => c.id === newChat.id);
            const chatKey = newChat.id;
            
            if (newChat.last_message) {
                const newMessageTime = newChat.last_message.created || 0;
                const oldMessageTime = oldChat && oldChat.last_message ? (oldChat.last_message.created || 0) : 0;
                
                // Если есть новое сообщение
                if (newMessageTime > oldMessageTime && oldChats.length > 0) {
                    // Проверяем, что это не наше собственное сообщение
                    const isOwnMessage = newChat.last_message.direction === 'out' || 
                                        newChat.last_message.type === 'outgoing';
                    
                    if (!isOwnMessage) {
                        hasNewMessages = true;
                        console.log('Новое сообщение в чате:', newChat.id);
                        
                        // Показываем десктопное уведомление
                        if ('Notification' in window && Notification.permission === 'granted') {
                            const userName = getChatUserName(newChat);
                            const messageText = newChat.last_message.content?.text || newChat.last_message.text || 'Новое сообщение';
                            new Notification(`${userName}`, {
                                body: messageText.substring(0, 100),
                                icon: getChatAvatar(newChat) || '/static/img/notification-icon.png'
                            });
                        }
                    }
                }
            }
        });
        
        // Воспроизводим звук если есть новые сообщения
        if (hasNewMessages && notificationSound) {
            try {
                notificationSound();
            } catch (e) {
                console.log('Не удалось воспроизвести звук:', e);
            }
        }
        
        chats = newChats;
        currentUserId = data.current_user_id;
        
        renderChats();
    } catch (error) {
        if (!silent) showError('Ошибка загрузки чатов: ' + error.message);
    } finally {
        if (!silent) hideLoading();
    }
}

// Запрашиваем разрешение на уведомления
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Helper функции для извлечения данных чата
function getChatUserName(chat) {
    if (chat.source === 'telegram') {
        return chat.name || 'Telegram Chat';
    } else {
        if (chat.users && chat.users.length > 0) {
            const otherUser = chat.users.find(u => u.id !== currentUserId) || chat.users[0];
            return otherUser ? (otherUser.name || `ID ${otherUser.id}`) : 'Пользователь';
        } else if (chat.user_id) {
            return `ID ${chat.user_id}`;
        }
        return 'Пользователь';
    }
}

function getChatAvatar(chat) {
    if (chat.source === 'telegram') {
        return chat.avatar || '';
    } else {
        if (chat.users && chat.users.length > 0) {
            const otherUser = chat.users.find(u => u.id !== currentUserId) || chat.users[0];
            if (otherUser && otherUser.public_user_profile && otherUser.public_user_profile.avatar) {
                const avatar = otherUser.public_user_profile.avatar;
                return avatar.images?.['48x48'] || avatar.default || '';
            }
        }
        return '';
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
        
        // Получаем имя пользователя и аватарку
        let userName = 'Пользователь';
        let userAvatar = '';
        
        // === TELEGRAM ===
        if (chat.source === 'telegram') {
            userName = chat.name || 'Telegram Chat';
            userAvatar = chat.avatar || '';
        }
        // === AVITO ===
        else {
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
                    // Аватарки находятся в public_user_profile.avatar
                    if (otherUser.public_user_profile && otherUser.public_user_profile.avatar) {
                        const avatar = otherUser.public_user_profile.avatar;
                        if (avatar.images && avatar.images['48x48']) {
                            userAvatar = avatar.images['48x48'];
                        } else if (avatar.default) {
                            userAvatar = avatar.default;
                        }
                    }
                }
            } else if (chat.user_id) {
                userName = `ID ${chat.user_id}`;
            }
        }
        
        // Получаем название объявления (подзаголовок)
        let itemTitle = '';
        if (chat.context && chat.context.value && chat.context.value.title) {
            itemTitle = chat.context.value.title;
        }
        
        // Определяем источник чата
        const source = chat.source || 'avito';
        const sourceBadge = source === 'telegram' 
            ? '<span class="source-badge source-badge-telegram">Telegram</span>'
            : '<span class="source-badge source-badge-avito">Avito</span>';
        
        // Проверяем непрочитанные сообщения
        const unreadCount = chat.unread_count || 0;
        
        // Для Telegram используем unread_count
        // Для Avito проверяем последнее сообщение
        let isUnread = false;
        if (chat.source === 'telegram') {
            isUnread = unreadCount > 0;
        } else {
            // Avito: проверяем, что последнее сообщение входящее и не прочитано
            const isIncoming = lastMessage.direction === 'in' || lastMessage.type === 'incoming';
            const isNotRead = !lastMessage.isRead;
            isUnread = isIncoming && isNotRead;
        }
        
        const unreadClass = isUnread ? 'unread' : '';
        const unreadBadge = unreadCount > 0 ? `<span class="unread-badge">${unreadCount}</span>` : '';
        
        return `
            <div class="chat-item ${chat.id === currentChatId ? 'active' : ''} ${unreadClass}" 
                 onclick="selectChat('${chat.id}')">
                <div class="chat-item-avatar-wrapper">
                    ${userAvatar ? `<img src="${escapeHtml(userAvatar)}" alt="${escapeHtml(userName)}" class="chat-item-avatar" onerror="this.style.display='none'">` : '<div class="chat-item-avatar-placeholder"></div>'}
                    ${unreadBadge}
                </div>
                <div class="chat-item-content">
                    <div class="chat-item-header">
                        <div class="chat-item-name-wrapper">
                            <div class="chat-item-name">${escapeHtml(userName)}</div>
                            ${sourceBadge}
                        </div>
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

async function loadMessages(chatId, silent = false) {
    if (!silent) {
        showLoading();
    }
    
    try {
        const response = await fetch(`/api/chats/${chatId}/messages`);
        const data = await response.json();
        
        if (data.error) {
            if (!silent) showError(data.error);
            return;
        }
        
        const oldMessagesCount = messages.length;
        messages = data.messages || [];
        
        // Сортируем сообщения по времени (старые сверху, новые внизу)
        messages.sort((a, b) => (a.created || 0) - (b.created || 0));
        
        // Если появились новые сообщения при тихом обновлении
        if (silent && messages.length > oldMessagesCount) {
            const isAtBottom = messagesList.scrollHeight - messagesList.scrollTop <= messagesList.clientHeight + 100;
            if (isAtBottom) {
                // Автопрокрутка вниз если мы были внизу
                setTimeout(() => {
                    messagesList.scrollTo({
                        top: messagesList.scrollHeight,
                        behavior: 'smooth'
                    });
                }, 100);
            }
        }
        
        // Сохраняем информацию о чате и текущем пользователе
        window.currentChatInfo = data.chat_info;
        window.currentUserId = data.current_user_id;
        
        // Получаем информацию о чате
        const chat = chats.find(c => c.id === chatId) || data.chat_info;
        let userName = 'Пользователь';
        let userAvatar = '';
        let itemTitle = '';
        
        if (chat) {
            // === TELEGRAM ===
            if (chat.source === 'telegram') {
                userName = chat.name || 'Telegram Chat';
                userAvatar = chat.avatar || '';
                itemTitle = chat.type === 'channel' ? 'Канал' : (chat.type === 'group' ? 'Группа' : '');
            }
            // === AVITO ===
            else {
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
                        if (otherUser.public_user_profile && otherUser.public_user_profile.avatar) {
                            const avatar = otherUser.public_user_profile.avatar;
                            if (avatar.images && avatar.images['48x48']) {
                                userAvatar = avatar.images['48x48'];
                            } else if (avatar.default) {
                                userAvatar = avatar.default;
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
        if (!silent) showError('Ошибка загрузки сообщений: ' + error.message);
    } finally {
        if (!silent) hideLoading();
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
    
    let html = '';
    let lastDate = null;
    
    messages.forEach((msg, index) => {
        // Добавляем разделитель дат
        const msgDate = new Date(msg.created * 1000);
        const dateStr = msgDate.toLocaleDateString('ru-RU', { 
            day: 'numeric', 
            month: 'long', 
            year: 'numeric' 
        });
        
        if (dateStr !== lastDate) {
            html += `<div class="date-delimiter"><span>${dateStr}</span></div>`;
            lastDate = dateStr;
        }
        
        html += renderSingleMessage(msg, index);
    });
    
    messagesList.innerHTML = html;
    
    // Прокрутка вниз
    messagesList.scrollTop = messagesList.scrollHeight;
}

function renderSingleMessage(msg, index) {
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
            // Аватарки находятся в public_user_profile.avatar
            if (author.public_user_profile && author.public_user_profile.avatar) {
                const avatar = author.public_user_profile.avatar;
                if (avatar.images && avatar.images['36x36']) {
                    authorAvatar = avatar.images['36x36'];
                } else if (avatar.default) {
                    authorAvatar = avatar.default;
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
                    ${!isOwn ? `<div class="message-item-author">${escapeHtml(authorName)}</div>` : ''}
                    <div class="message-item-time">${time}</div>
                    ${canDelete ? `<button class="btn-delete-message" onclick="deleteMessage('${msg.id}')" title="Удалить">🗑️</button>` : ''}
                </div>
                <div class="message-item-text">${escapeHtml(text)}</div>
            </div>
        </div>
    `;
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



