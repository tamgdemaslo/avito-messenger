/**
 * WhatsApp Web.js Microservice
 * Предоставляет REST API для интеграции WhatsApp в CRM
 */

const express = require('express');
const cors = require('cors');
const qrcode = require('qrcode');
const { Client, LocalAuth } = require('whatsapp-web.js');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// WhatsApp клиент
let client = null;
let qrCodeData = null;
let isReady = false;
let isAuthenticating = false;

// Инициализация WhatsApp клиента
function initWhatsAppClient() {
    if (client) {
        return;
    }

    console.log('🟢 Инициализация WhatsApp клиента...');
    
    client = new Client({
        authStrategy: new LocalAuth({
            clientId: 'avito-crm-whatsapp'
        }),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ],
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined
        }
    });

    // QR код для авторизации
    client.on('qr', async (qr) => {
        console.log('📱 QR код получен');
        isAuthenticating = true;
        isReady = false;
        
        try {
            qrCodeData = await qrcode.toDataURL(qr);
            console.log('✅ QR код готов для отображения');
        } catch (err) {
            console.error('Ошибка генерации QR кода:', err);
        }
    });

    // Клиент готов
    client.on('ready', () => {
        console.log('✅ WhatsApp клиент готов!');
        isReady = true;
        isAuthenticating = false;
        qrCodeData = null;
    });

    // Авторизация успешна
    client.on('authenticated', () => {
        console.log('✅ WhatsApp авторизован');
        isAuthenticating = false;
    });

    // Ошибка авторизации
    client.on('auth_failure', (msg) => {
        console.error('❌ Ошибка авторизации WhatsApp:', msg);
        isAuthenticating = false;
        isReady = false;
    });

    // Отключение
    client.on('disconnected', (reason) => {
        console.log('⚠️ WhatsApp отключен:', reason);
        isReady = false;
        isAuthenticating = false;
    });

    // Новое сообщение (для webhook в будущем)
    client.on('message', async (message) => {
        console.log('📨 Новое сообщение:', message.from);
    });

    // Запуск клиента
    client.initialize();
}

// API Endpoints

// Статус клиента
app.get('/status', (req, res) => {
    res.json({
        ready: isReady,
        authenticating: isAuthenticating,
        hasQR: qrCodeData !== null
    });
});

// Получить QR код
app.get('/qr', (req, res) => {
    if (!qrCodeData) {
        return res.status(404).json({ error: 'QR код не доступен' });
    }
    res.json({ qr: qrCodeData });
});

// Получить список чатов
app.get('/chats', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не готов' });
    }

    try {
        const limit = parseInt(req.query.limit) || 30;
        const chats = await client.getChats();
        
        // Фильтруем только личные чаты (не группы)
        const privateChats = chats
            .filter(chat => !chat.isGroup)
            .slice(0, limit);

        const result = [];

        for (const chat of privateChats) {
            try {
                const lastMessage = chat.lastMessage;

                const chatData = {
                    id: `wa_${chat.id._serialized}`,
                    source: 'whatsapp',
                    original_id: chat.id._serialized,
                    name: chat.name || 'WhatsApp User',
                    unread_count: chat.unreadCount || 0,
                    created: lastMessage ? lastMessage.timestamp : 0,
                    updated: lastMessage ? lastMessage.timestamp : 0,
                    type: 'private',
                    has_photo: false
                };

                // Последнее сообщение
                if (lastMessage) {
                    chatData.last_message = {
                        id: lastMessage.id._serialized,
                        text: lastMessage.body || '',
                        created: lastMessage.timestamp,
                        from_id: lastMessage.from
                    };
                }

                result.push(chatData);
            } catch (error) {
                console.log(`⚠️ Ошибка обработки чата ${chat.id._serialized}:`, error.message);
                continue;
            }
        }

        res.json(result);
    } catch (error) {
        console.error('Ошибка получения чатов:', error);
        res.status(500).json({ error: error.message });
    }
});

// Получить сообщения чата
app.get('/chats/:chatId/messages', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не готов' });
    }

    try {
        const chatId = req.params.chatId.replace('wa_', '');
        const limit = parseInt(req.query.limit) || 30;
        
        const chat = await client.getChatById(chatId);
        const messages = await chat.fetchMessages({ limit });

        const result = messages.map(msg => ({
            id: `wa_${msg.id._serialized}`,
            original_id: msg.id._serialized,
            author_id: msg.from,
            created: msg.timestamp,
            text: msg.body || '',
            type: msg.type === 'chat' ? 'text' : msg.type,
            direction: msg.fromMe ? 'out' : 'in',
            isRead: msg.fromMe ? true : !msg.id.fromMe
        }));

        res.json(result);
    } catch (error) {
        console.error('Ошибка получения сообщений:', error);
        res.status(500).json({ error: error.message });
    }
});

// Отправить сообщение
app.post('/messages/send', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не готов' });
    }

    try {
        const { chat_id, message } = req.body;
        const chatId = chat_id.replace('wa_', '');
        
        const chat = await client.getChatById(chatId);
        const sentMessage = await chat.sendMessage(message);

        res.json({
            success: true,
            message_id: sentMessage.id._serialized,
            timestamp: sentMessage.timestamp
        });
    } catch (error) {
        console.error('Ошибка отправки сообщения:', error);
        res.status(500).json({ error: error.message });
    }
});

// Пометить чат как прочитанный
app.post('/chats/:chatId/read', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp не готов' });
    }

    try {
        const chatId = req.params.chatId.replace('wa_', '');
        const chat = await client.getChatById(chatId);
        await chat.sendSeen();

        res.json({ success: true });
    } catch (error) {
        console.error('Ошибка пометки прочитанным:', error);
        res.status(500).json({ error: error.message });
    }
});

// Запуск сервера
app.listen(PORT, () => {
    console.log(`🟢 WhatsApp service running on port ${PORT}`);
    initWhatsAppClient();
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('⚠️ Остановка WhatsApp сервиса...');
    if (client) {
        await client.destroy();
    }
    process.exit(0);
});

