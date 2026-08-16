# DeskMate — мультимодальный Telegram-ассистент

![DeskMate cover](docs/cover.png)

Ops-ассистент студии [NeiroBridge](https://neirobridge.ru): ответы по базе знаний, голос, Vision и генерация изображений в Telegram.

**Попробовать:** [@DeskMate_NB_bot](https://t.me/DeskMate_NB_bot) · **Кейс на сайте:** [neirobridge.ru/cases/deskmate](https://neirobridge.ru/cases/deskmate)

## Зачем это бизнесу

DeskMate снимает ручной поиск по документам, FAQ и переписке: сотрудник задаёт вопрос в Telegram и получает ответ по утверждённым материалам компании.  
Повторные вопросы ускоряются кэшем; команда `/stats` показывает время ответа, долю кэша и объём запросов — без хранения телефонов и ФИО (только `user_id`).

| Метрика | Польза |
|--------|--------|
| Время ответа (мс) | Видно узкие места: STT, RAG, LLM |
| Доля ответов из кэша | Экономия API и быстрее повторные вопросы |
| Запросы за 24 часа | Нагрузка и популярные сценарии |

## Возможности

- **Текст** — диалог с GPT-4o, история сообщений
- **RAG** — ответы из базы знаний (ChromaDB) с указанием источника
- **Голос** — Whisper (STT) + TTS (`/mode voice`)
- **Vision** — анализ фото и скриншотов (GPT-4o Vision)
- **Генерация изображений** — gpt-image-1 через ProxyAPI
- **Метрики** — SQLite-логи, кэш ответов, `/stats`

## Стек

- Python 3.10+, pyTelegramBotAPI
- OpenAI через [ProxyAPI](https://proxyapi.ru)
- LangChain + ChromaDB (RAG)
- SQLite + JSON-кэш
- Cloudflare Worker — прокси Telegram Bot API для РФ

## Быстрый старт

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # заполнить ключи
python main.py
```

Или `run.bat` на Windows.

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_API_URL` | URL Cloudflare Worker (без `/bot...`) |
| `OPENAI_API_KEY` | Ключ ProxyAPI |
| `USE_PROXYAPI` | `true` (по умолчанию) |
| `IMAGE_GEN_MODEL` | `gpt-image-1` (по умолчанию) |

### Cloudflare Worker

Код прокси: [`cloudflare/telegram-proxy.js`](cloudflare/telegram-proxy.js).

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/mode text\|voice\|rag` | Режим работы |
| `/stats` | Статус RAG и метрики |
| `/image <описание>` | Генерация изображения |
| `/reset` | Сброс истории диалога |

## Метрики и логирование

1. Пользователь отправляет запрос  
2. Проверка кэша → при попадании ответ сразу (`from_cache`)  
3. Иначе RAG/LLM → ответ  
4. Запись в SQLite: query, response, user_id, mode, response_time_ms, from_cache  

Экспорт CSV:

```python
from utils.db_logger import db_logger
print(db_logger.export_csv())
```

`data/logs.db` и `data/response_cache.json` в git не попадают.

## Структура проекта

```
handlers/       — команды и входящие сообщения
services/       — OpenAI, router, STT/TTS, Vision, image generation
rag/            — индексация и поиск в ChromaDB
utils/          — логи, SQLite-метрики, кэш, сессии
data/documents/ — файлы базы знаний (txt)
docs/           — обложка и материалы портфолио
cloudflare/     — Worker для Telegram API
```

## Пайплайн

```
Пользователь (Telegram) → Cloudflare Worker → handlers/
  → кэш? → ProxyAPI / ChromaDB
  → SQLite log (время, кэш)
  → ответ в Telegram
```

## База знаний RAG

Файлы в `data/documents/` индексируются при старте.  
Режим: `/mode rag`

## Деплой на VPS

```bash
cd /opt/deskmate-bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
nano .env
screen -S deskmate
python main.py
```

## Ограничения (РФ + Telegram)

Прямой доступ к `api.telegram.org` из России ограничен — используется Cloudflare Worker.  
Медиа через прокси может падать по таймауту (инфраструктурное ограничение).

## Лицензия

MIT

---

[neirobridge.ru](https://neirobridge.ru) · [@DeskMate_NB_bot](https://t.me/DeskMate_NB_bot) · [GitHub](https://github.com/NeiroBridge/deskmate-bot)
