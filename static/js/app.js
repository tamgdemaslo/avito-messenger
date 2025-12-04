// Avito Messenger Frontend Application

let currentChatId = null;
let chats = [];
let messages = [];
let messagesCache = {}; // Кэш сообщений для быстрого переключения
let currentLoadController = null; // Контроллер для отмены предыдущих запросов
let loadRequestId = 0; // Счетчик запросов для игнорирования старых

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
let receiveSound = null;
let sendSound = null;

// Создаем звуки уведомлений
function initNotificationSound() {
    // Звук получения сообщения
    receiveSound = new Audio('/static/sounds/popup-sound-modal.mp3');
    receiveSound.volume = 0.5;
    
    // Звук отправки сообщения
    sendSound = new Audio('/static/sounds/beautiful-sms-notification-sound.mp3');
    sendSound.volume = 0.5;
    
    // Если файлы не загрузились, используем синтетический звук
    receiveSound.addEventListener('error', () => {
        console.log('Звуковой файл получения не найден, используем синтетический звук');
        receiveSound = createSyntheticSound(600, 0.3);
    });
    
    sendSound.addEventListener('error', () => {
        console.log('Звуковой файл отправки не найден, используем синтетический звук');
        sendSound = createSyntheticSound(800, 0.2);
    });
}

// Создание синтетического звука (запасной вариант)
function createSyntheticSound(frequency, volume) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    return {
        play: () => {
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = frequency;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(volume, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        }
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
    // Обновляем ТОЛЬКО текущий открытый чат каждые 3 секунды
    // Список чатов обновляем реже (каждые 10 секунд)
    
    let chatRefreshCounter = 0;
    
    autoRefreshInterval = setInterval(async () => {
        chatRefreshCounter++;
        
        // Обновляем список чатов каждые 10 секунд (каждый 3-й раз)
        if (chatRefreshCounter % 3 === 0) {
            await loadChats(true);
        }
        
        // Обновляем сообщения ТОЛЬКО текущего открытого чата
        if (currentChatId) {
            await loadMessages(currentChatId, true);
        }
    }, 3000); // 3 секунды
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
        
        // НЕ делаем никакой предзагрузки - только по требованию!
        
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
        if (hasNewMessages && receiveSound) {
            try {
                receiveSound.play();
            } catch (e) {
                console.log('Не удалось воспроизвести звук:', e);
            }
        }
        
        chats = newChats;
        currentUserId = data.current_user_id;
        
        renderChats();
        
        // Ленивая загрузка аватарок Telegram в фоне
        if (!silent) {
            lazyLoadTelegramAvatars();
        }
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

// Ленивая загрузка аватарок Telegram (по одной в фоне)
let avatarLoadQueue = [];
let isLoadingAvatars = false;

async function lazyLoadTelegramAvatars() {
    // Находим все Telegram чаты с аватарками
    const telegramChatsWithPhotos = chats.filter(chat => 
        chat.source === 'telegram' && 
        chat.has_photo && 
        !chat.avatar
    );
    
    if (telegramChatsWithPhotos.length === 0) {
        return;
    }
    
    console.log(`🖼️ Lazy loading ${telegramChatsWithPhotos.length} Telegram avatars...`);
    
    // Загружаем по одной с задержкой (не перегружаем сервер)
    for (let i = 0; i < telegramChatsWithPhotos.length; i++) {
        const chat = telegramChatsWithPhotos[i];
        
        // Небольшая задержка между запросами
        await new Promise(resolve => setTimeout(resolve, 200));
        
        try {
            const response = await fetch(`/api/telegram/avatar/${chat.id}`);
            const data = await response.json();
            
            if (data.success && data.avatar) {
                // Обновляем чат с аватаркой
                const chatInList = chats.find(c => c.id === chat.id);
                if (chatInList) {
                    chatInList.avatar = data.avatar;
                    // Перерисовываем список чатов
                    renderChats();
                    console.log(`✅ Loaded avatar for ${chat.name}`);
                }
            }
        } catch (error) {
            console.log(`⚠️ Failed to load avatar for ${chat.name}:`, error.message);
        }
    }
    
    console.log(`✅ All avatars loaded`);
}

// Helper функции для извлечения данных чата
function getChatUserName(chat) {
    if (chat.source === 'whatsapp') {
        return chat.name || 'WhatsApp User';
    } else if (chat.source === 'telegram') {
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
        const msgType = lastMessage.type || 'text';
        
        // Проверяем тип медиа
        if (msgType === 'image' || msgType === 'photo') {
            preview = '🖼️ Изображение';
        } else if (msgType === 'voice' || msgType === 'ptt' || msgType === 'audio') {
            preview = '🎤 Голосовое сообщение';
        } else if (msgType === 'video') {
            preview = '🎥 Видео';
        } else if (msgType === 'document') {
            preview = '📄 Документ';
        } else if (msgType === 'sticker') {
            preview = '🎨 Стикер';
        } else if (lastMessage.content) {
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
        
        // === WHATSAPP ===
        if (chat.source === 'whatsapp') {
            userName = chat.name || 'WhatsApp User';
            userAvatar = ''; // WhatsApp без аватарок (пока)
        }
        // === TELEGRAM ===
        else if (chat.source === 'telegram') {
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
        
        // Определяем источник чата - компактные иконки
        const source = chat.source || 'avito';
        let sourceBadge = '';
        
        if (source === 'whatsapp') {
            sourceBadge = '<span class="source-badge source-badge-whatsapp" title="WhatsApp">W</span>';
        } else if (source === 'telegram') {
            sourceBadge = `<span class="source-badge source-badge-telegram" title="Telegram">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
                    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.009-1.252-.241-1.865-.44-.752-.244-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.477-1.635.099-.002.321-.022.465.138.121.134.154.315.17.46-.002.104-.005.677-.01.962z"/>
                </svg>
               </span>`;
        } else {
            sourceBadge = '<span class="source-badge source-badge-avito" title="Avito">A</span>';
        }
        
        // Проверяем непрочитанные сообщения
        const unreadCount = chat.unread_count || 0;
        
        // Определяем непрочитанные по источнику
        let isUnread = false;
        if (chat.source === 'whatsapp' || chat.source === 'telegram') {
            // WhatsApp и Telegram используют unread_count
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
    // Отменяем предыдущую загрузку если она еще идет
    if (currentLoadController) {
        currentLoadController.abort();
    }
    
    currentChatId = chatId;
    renderChats();
    
    // Показываем форму сразу
    replyForm.style.display = 'block';
    
    // Загружаем сообщения (не ждем завершения)
    loadMessages(chatId);
    
    // Помечаем чат прочитанным в фоне
    markChatAsRead(chatId);
}

async function markChatAsRead(chatId) {
    try {
        const response = await fetch(`/api/chats/${chatId}/read`, {
            method: 'POST'
        });
        
        if (response.ok) {
            // Обновляем локальный список чатов, чтобы сразу убрать бейдж
            const chat = chats.find(c => c.id === chatId);
            if (chat) {
                chat.unread_count = 0;
                if (chat.last_message) {
                    chat.last_message.isRead = true;
                }
                renderChats(); // Перерисовываем список чатов
            }
        }
    } catch (error) {
        console.error('Error marking chat as read:', error);
    }
}

async function loadMessages(chatId, silent = false) {
    // Генерируем уникальный ID для этого запроса
    const requestId = ++loadRequestId;
    
    // Отменяем предыдущий fetch
    if (currentLoadController) {
        currentLoadController.abort();
    }
    currentLoadController = new AbortController();
    
    console.log(`🔄 Loading chat ${chatId}, requestId: ${requestId}`);
    
    // Проверяем кэш
    const hasCache = messagesCache[chatId];
    const cacheAge = hasCache ? (Date.now() - messagesCache[chatId].timestamp) : Infinity;
    const isCacheFresh = cacheAge < 30000; // Кэш свежий если < 30 секунд
    
    if (hasCache) {
        messages = messagesCache[chatId].messages;
        window.currentChatInfo = messagesCache[chatId].chatInfo;
        window.currentUserId = messagesCache[chatId].userId;
        
        // Мгновенно показываем закэшированные данные
        renderChatHeader(messagesCache[chatId].chatInfo);
        renderMessages();
        
        // Прокрутка вниз
        if (!silent) {
            messagesList.scrollTo({
                top: messagesList.scrollHeight,
                behavior: 'auto'
            });
        }
        
        console.log(`⚡ Loaded from cache ${chatId} (age: ${Math.round(cacheAge/1000)}s)`);
        
        // Если кэш свежий (< 30 сек) И это не тихое обновление - НЕ делаем запрос!
        if (isCacheFresh && !silent) {
            console.log(`✅ Cache is fresh, skipping API request`);
            return;
        }
    } else if (!silent && !hasCache) {
        // Показываем скелетон только если нет кэша
        showMessagesSkeleton();
    }
    
    // Загружаем данные
    try {
        const fetchStartTime = Date.now();
        const response = await fetch(`/api/chats/${chatId}/messages`, {
            signal: currentLoadController.signal
        });
        const fetchEndTime = Date.now();
        console.log(`📥 Fetch completed in ${fetchEndTime - fetchStartTime}ms`);
        
        // КРИТИЧНО: Проверяем что это все еще актуальный запрос
        if (requestId !== loadRequestId) {
            console.log(`❌ Ignoring old request ${requestId} (current: ${loadRequestId})`);
            return; // Игнорируем результат старого запроса
        }
        
        // КРИТИЧНО: Проверяем что chatId все еще текущий
        if (chatId !== currentChatId) {
            console.log(`❌ Chat changed from ${chatId} to ${currentChatId}`);
            return; // Пользователь переключился на другой чат
        }
        
        const data = await response.json();
        
        if (data.error) {
            if (!silent) showError(data.error);
            return;
        }
        
        const oldMessagesCount = messages.length;
        messages = data.messages || [];
        
        // Сортируем сообщения по времени
        messages.sort((a, b) => (a.created || 0) - (b.created || 0));
        
        // Сохраняем в кэш
        messagesCache[chatId] = {
            messages: messages,
            chatInfo: data.chat_info,
            userId: data.current_user_id,
            timestamp: Date.now()
        };
        
        // Сохраняем информацию
        window.currentChatInfo = data.chat_info;
        window.currentUserId = data.current_user_id;
        
        // Рендерим
        renderChatHeader(data.chat_info);
        renderMessages();
        
        // Прокрутка вниз
        if (!silent) {
            messagesList.scrollTo({
                top: messagesList.scrollHeight,
                behavior: 'auto'
            });
        }
        
        console.log(`✅ Rendered chat ${chatId}, ${messages.length} messages`);
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log(`⚠️ Request aborted for ${chatId}`);
            return;
        }
        if (!silent) showError('Ошибка загрузки: ' + error.message);
    }
}

// Показать скелетон загрузки сообщений
function showMessagesSkeleton() {
    // Показываем заголовок из списка чатов
    const chat = chats.find(c => c.id === currentChatId);
    if (chat) {
        renderChatHeader(chat);
    }
    
    // Показываем скелетон сообщений
    messagesList.innerHTML = `
        <div class="messages-skeleton">
            <div class="skeleton-message"></div>
            <div class="skeleton-message own"></div>
            <div class="skeleton-message"></div>
            <div class="skeleton-message own"></div>
            <div class="skeleton-message"></div>
        </div>
    `;
}

// Отдельная функция для рендеринга заголовка чата
function renderChatHeader(chatInfo) {
    const chat = chats.find(c => c.id === currentChatId) || chatInfo;
    let userName = 'Пользователь';
    let userAvatar = '';
    let itemTitle = '';
    
    if (chat) {
        // === WHATSAPP ===
        if (chat.source === 'whatsapp') {
            userName = chat.name || 'WhatsApp User';
            userAvatar = '';
            itemTitle = 'WhatsApp';
        }
        // === TELEGRAM ===
        else if (chat.source === 'telegram') {
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
    let mediaHtml = '';
    
    // Проверяем тип сообщения
    const messageType = msg.type || 'text';
    
    if (messageType === 'image' || messageType === 'photo') {
        // Изображение
        mediaHtml = `<div class="media-message image-message">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
            <span>Изображение</span>
        </div>`;
        text = msg.content?.text || msg.text || '';
    } else if (messageType === 'voice' || messageType === 'ptt' || messageType === 'audio') {
        // Голосовое сообщение
        mediaHtml = `<div class="media-message voice-message">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
            <span>Голосовое сообщение</span>
        </div>`;
        text = '';
    } else if (messageType === 'video') {
        // Видео
        mediaHtml = `<div class="media-message video-message">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="23 7 16 12 23 17 23 7"></polygon>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
            </svg>
            <span>Видео</span>
        </div>`;
        text = msg.content?.text || msg.text || '';
    } else if (messageType === 'document') {
        // Документ
        mediaHtml = `<div class="media-message document-message">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                <polyline points="13 2 13 9 20 9"></polyline>
            </svg>
            <span>Документ</span>
        </div>`;
        text = msg.content?.text || msg.text || '';
    } else {
        // Текстовое сообщение
        if (msg.content && msg.content.text) {
            text = msg.content.text;
        } else if (typeof msg.content === 'string') {
            text = msg.content;
        } else if (msg.text) {
            text = msg.text;
        } else {
            text = '[Сообщение без текста]';
        }
    }
    
    // Проверяем можно ли удалить сообщение (только свои, не старше часа)
    const canDelete = isOwn && (Date.now() - msg.created * 1000) < 3600000;
    
    // Статус доставки (галочки) - только для исходящих
    let deliveryStatus = '';
    if (isOwn) {
        if (msg.isPending) {
            // Отправляется - одна галочка
            deliveryStatus = '<span class="delivery-status pending" title="Отправляется">✓</span>';
        } else if (msg.isRead) {
            // Прочитано - две синие галочки
            deliveryStatus = '<span class="delivery-status read" title="Прочитано">✓✓</span>';
        } else {
            // Доставлено - две серые галочки
            deliveryStatus = '<span class="delivery-status delivered" title="Доставлено">✓✓</span>';
        }
    }
    
    return `
        <div class="message-item ${isOwn ? 'own' : ''} ${msg.isPending ? 'pending' : ''}" data-message-id="${msg.id}">
            ${!isOwn && authorAvatar ? `<img src="${escapeHtml(authorAvatar)}" alt="${escapeHtml(authorName)}" class="message-avatar" onerror="this.style.display='none'">` : ''}
            <div class="message-content">
                <div class="message-item-header">
                    ${!isOwn ? `<div class="message-item-author">${escapeHtml(authorName)}</div>` : ''}
                    <div class="message-item-time">${time} ${deliveryStatus}</div>
                    ${canDelete ? `<button class="btn-delete-message" onclick="deleteMessage('${msg.id}')" title="Удалить">🗑️</button>` : ''}
                </div>
                ${mediaHtml ? mediaHtml : ''}
                ${text ? `<div class="message-item-text">${escapeHtml(text)}</div>` : ''}
            </div>
        </div>
    `;
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || !currentChatId) {
        return;
    }
    
    // Очищаем поле ввода сразу (мгновенная отправка)
    messageInput.value = '';
    
    // Воспроизводим звук отправки
    if (sendSound) {
        try {
            sendSound.play();
        } catch (e) {
            console.log('Не удалось воспроизвести звук отправки:', e);
        }
    }
    
    // Создаем оптимистичное сообщение (сразу показываем в UI)
    const optimisticMessage = {
        id: `temp_${Date.now()}`,
        content: { text: text },
        text: text,
        created: Date.now() / 1000,
        type: 'outgoing',
        direction: 'out',
        author_id: currentUserId || window.currentUserId,
        isPending: true, // Статус "отправляется" - одна галочка
        isRead: false
    };
    
    // Добавляем в список сообщений сразу
    messages.push(optimisticMessage);
    renderMessages(); // Перерисовываем с новым сообщением
    
    // Прокручиваем вниз
    messagesList.scrollTo({
        top: messagesList.scrollHeight,
        behavior: 'smooth'
    });
    
    // Отправляем сообщение в фоне без блокировки UI
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
            // Удаляем оптимистичное сообщение при ошибке
            messages = messages.filter(m => m.id !== optimisticMessage.id);
            renderMessages();
            showError(data.error);
            // Возвращаем текст обратно в поле если ошибка
            messageInput.value = text;
            return;
        }
        
        // Убираем статус "pending" и обновляем через 1 секунду
        setTimeout(() => {
            loadMessages(currentChatId, true);
            loadChats(true);
        }, 1000);
    } catch (error) {
        // Удаляем оптимистичное сообщение при ошибке
        messages = messages.filter(m => m.id !== optimisticMessage.id);
        renderMessages();
        showError('Ошибка отправки сообщения: ' + error.message);
        // Возвращаем текст обратно в поле если ошибка
        messageInput.value = text;
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



