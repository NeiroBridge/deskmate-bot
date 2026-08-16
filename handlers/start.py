"""
Start and Help Command Handlers.
Handles /start and /help commands using pyTelegramBotAPI.
"""

from telebot import types
from bot import bot
from utils.logging import logger
from utils.helpers import user_sessions
from config import BotMode, DEFAULT_MODE


@bot.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Handle /start command."""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"User {user_id} started the bot")
    
    # Initialize user session
    user_sessions.set_mode(user_id, DEFAULT_MODE)
    
    welcome_text = f"""👋 Привет, {user_name}!

Я DeskMate — ops-ассистент студии NeiroBridge.
Сайт: https://neirobridge.ru

Что умею:
🔤 Текст — вопросы по продуктам и процессам
📚 RAG — ответы из базы знаний (цены, сценарии)
🎤 Голос — диктуй задачи на ходу
📸 Vision — разбор скринов брифов

Попробуй спросить:
• Сколько стоит AI-агент для заявок?
• Что входит в бесплатную диагностику?

Команды (отправляй по одной):
/help
/mode rag
/stats
/reset"""
    
    await bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    """Handle /help command."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested help")
    
    help_text = """📖 **Полное руководство по боту**

**🔤 Текстовый режим**
Просто напиши сообщение - я отвечу используя GPT-4o.

**🎤 Голосовой режим**
1. Отправь голосовое сообщение
2. Я распознаю речь через Whisper
3. Обработаю запрос
4. Отвечу голосом + текстом

**📸 Режим Vision**
1. Отправь фото
2. Можешь добавить подпись с вопросом
3. Получи детальный анализ изображения

**📚 Режим RAG (База знаний)**
1. Переключись: /mode rag
2. Загрузи документы в папку data/documents/
3. Задавай вопросы по документам
4. Получай ответы с указанием источников

**⚙️ Команды управления:**

/mode <режим> - переключить режим
  • text - текстовый (по умолчанию)
  • voice - голосовой
  • vision - анализ изображений
  • rag - база знаний

/voice <имя> - выбрать голос
  • alloy - нейтральный (по умолчанию)
  • echo - мужской
  • nova - женский
  • fable - британский
  • onyx - глубокий мужской
  • shimmer - теплый женский

/reset - очистить историю диалога
/stats - статистика RAG и метрики (время ответа, кэш)
/voices - список доступных голосов

**💡 Примеры использования:**

1. "Объясни квантовую физику простыми словами"
2. [Голосовое] "Какая погода в Москве?"
3. [Фото документа] "Извлеки данные из этого чека"
4. [В режиме RAG] "Найди информацию о проекте X"

**🔧 Технологии:**
• GPT-4o для текста
• GPT-4 Vision для изображений
• Whisper для распознавания речи
• TTS-1 для синтеза речи
• ChromaDB + LangChain для RAG

Нужна помощь? Просто спроси! 😊"""
    
    await bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    """Handle /reset command - clear conversation history."""
    user_id = message.from_user.id
    
    user_sessions.clear_history(user_id)
    logger.info(f"User {user_id} cleared conversation history")
    
    await bot.send_message(
        message.chat.id,
        "✅ История диалога очищена!\n\n"
        "Начнем с чистого листа. Чем могу помочь?"
    )


@bot.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    """Handle /stats — RAG index + interaction metrics."""
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested stats")

    rag_block = "⚠️ База знаний недоступна."
    try:
        from rag.query import get_knowledge_base_stats

        stats = get_knowledge_base_stats()
        if "error" in stats:
            rag_block = f"⚠️ RAG: {stats['error']}"
        else:
            total_docs = stats.get("total_documents", 0)
            persist_dir = stats.get("persist_directory", "N/A")
            status = (
                "✅ База знаний готова"
                if total_docs > 0
                else "⚠️ База пуста — добавьте файлы в data/documents/"
            )
            rag_block = (
                f"📚 База знаний (RAG)\n"
                f"• Фрагментов в индексе: {total_docs}\n"
                f"• Директория: {persist_dir}\n"
                f"• {status}"
            )
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        rag_block = "⚠️ Ошибка статистики базы знаний."

    metrics_block = "⚠️ Метрики взаимодействий недоступны."
    try:
        from utils.db_logger import db_logger
        from utils.response_cache import response_cache

        m = db_logger.get_stats(hours=24)
        avg = m["avg_response_time_ms"]
        median = m["median_response_time_ms"]
        metrics_block = (
            f"📈 Метрики ассистента\n"
            f"• Всего запросов: {m['total_requests']}\n"
            f"• За последние {m['hours_window']} ч: {m['requests_last_hours']}\n"
            f"• Из кэша: {m['cached_requests']} ({m['cache_hit_rate_pct']}%)\n"
            f"• Среднее время ответа: {avg if avg is not None else '—'} мс\n"
            f"• Медиана времени: {median if median is not None else '—'} мс\n"
            f"• Записей в кэше: {response_cache.size()}\n"
            f"• Логи: {m['db_path']}"
        )
    except Exception as e:
        logger.error(f"Error getting interaction metrics: {e}")

    await bot.send_message(
        message.chat.id,
        f"📊 Статистика DeskMate\n\n{rag_block}\n\n{metrics_block}\n\n"
        f"Для вопросов по документам: /mode rag",
    )
