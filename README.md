<div align="center">

# 🛰️ DARK Reposter

**Автономный кросспостер нового поколения из Telegram в глобальные и децентрализованные соцсети**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![aiogram 3](https://img.shields.io/badge/aiogram-v3.x-informational.svg?style=flat-square&logo=telegram)](https://github.com/aiogram/aiogram)
[![Buffer GraphQL](https://img.shields.io/badge/Buffer-GraphQL%20API-orange.svg?style=flat-square&logo=buffer)](https://buffer.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

[X (Twitter)](https://twitter.com) • [Bluesky](https://bsky.app) • [Mastodon](https://joinmastodon.org) • [Threads](https://threads.net) • [LinkedIn](https://linkedin.com)

</div>

---

## 🌌 О проекте и манифест

**Telegram** — непревзойдённая платформа для ведения авторских каналов, комфортного лонгрида, живого комьюнити и публикации контента без алгоритмического шума. Для многих авторов, исследователей и энтузиастов Telegram стал настоящей творческой мастерской.

Однако, оставаясь исключительно внутри Telegram, мы часто замыкаемся в собственном информационном пузыре. За его пределами живёт и дышит огромный открытый мир: бурные обсуждения в **X (Twitter)**, зарождающийся свободный децентрализованный веб в **Bluesky** и **Mastodon**, профессиональные сети **LinkedIn** и альтернативные каналы **Threads**.

Тратить драгоценное время на ручной копипаст каждого поста, пересчёт символов и подгонку картинок под разные интерфейсы — скучно и неэффективно.

**DARK Reposter** создан, чтобы решить эту проблему раз и навсегда:
> **Вы просто публикуете пост в любимом Telegram-канале.**  
> Бот моментально подхватывает его, аккуратно адаптирует текст под лимиты каждой площадки, забирает прикреплённые изображения и мгновенно публикует в ваших подключённых соцсетях.

---

## ✨ Ключевые возможности

- 🚀 **Один источник — глобальный охват:** Публикация в один клик в X/Twitter, Bluesky, Mastodon, Threads и LinkedIn через единый шлюз Buffer GraphQL API.
- 🧠 **Интеллектуальная адаптация текста:** Никаких случайных обрывов фраз на полуслове! Бот сохраняет ключевые абзацы, выносит ссылки и аккуратно укладывает мысль в лимит (280 символов для X, 300 для Bluesky, 500 для Mastodon и т.д.).
- 📸 **Умная работа с изображениями и альбомами:**
  - Поддержка одиночных фото и фотоальбомов (до 4 медиа-файлов).
  - **Zero-Config Media:** благодаря интеграции с Telegram Bot CDN сервису **не требуются** публичный белый IP, домен, reverse-proxy или dynamic DNS! Buffer скачивает медиа напрямую через защищённый шлюз Telegram.
- 🏷️ **Теги тонкого управления прямо в посте:**
  - `#noauto` — отменить репост этого сообщения.
  - `#draft` — обработать и сохранить в локальную базу, но не публиковать.
  - `#xonly`, `#nobluesky`, `#nomastodon`, `#nothreads`, `#nolinkedin` — выборочная отправка только на нужные платформы.
  *(Все служебные теги автоматически удаляются перед отправкой в соцсети).*
- 🗄️ **Локальная SQLite база данных:** Полная история публикаций, дедупликация сообщений, сохранение ID постов и статусов доставки.
- 🛡️ **Надёжность и автономность 24/7:**
  - Готовая конфигурация для **systemd user-service** с включённым `Linger=yes`.
  - Автоматический перезапуск после ребута ОС, отключения электричества или сбоя интернет-соединения.
  - Мягкий graceful shutdown при сигналах `SIGTERM` / `SIGINT`.

---

## 🛠 Архитектура

```
  ┌─────────────────────────┐
  │ Telegram Channel        │
  │ (автор публикует пост)  │
  └────────────┬────────────┘
               │ (Long Polling via aiogram 3)
               ▼
  ┌─────────────────────────────────────────────────────────┐
  │                     DARK Reposter                       │
  │  1. Очистка от служебных тегов (#noauto, #xonly, etc.)  │
  │  2. Адаптация длины текста под лимиты площадок          │
  │  3. Сборка альбомов и получение CDN-ссылок на медиа     │
  │  4. Запись в локальную SQLite (история и дедуп)         │
  └────────────┬────────────────────────────────────────────┘
               │ (GraphQL API shareNow)
               ▼
  ┌─────────────────────────┐
  │       Buffer API        │
  └────┬───────┬───────┬────┘
       │       │       │
       ▼       ▼       ▼
     [ X ]  [Bluesky] [Mastodon] [Threads] [LinkedIn]
```

---

## 🚀 Быстрый старт

### 1. Предварительные требования
* Python 3.11 или выше
* Telegram-канал и Telegram-бот (создаётся через [@BotFather](https://t.me/BotFather))
* Аккаунт на [Buffer.com](https://buffer.com) (бесплатный тариф поддерживает 3 канала, например Twitter + Bluesky + Mastodon)

### 2. Клонирование и установка

```bash
git clone https://github.com/Dark-city-beta/dark-reposter.git
cd dark-reposter

# Создание виртуального окружения
python3 -m venv .venv
source .venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 3. Настройка окружения (`.env`)

Скопируйте шаблон конфигурации:
```bash
cp .env.example .env
nano .env
```

Заполните основные параметры:
* `TELEGRAM_BOT_TOKEN`: токен от BotFather.
* `TELEGRAM_CHANNEL_ID`: `@username` вашего канала или его числовой ID (например, `-1002304224672`).
  * *Важно:* добавьте созданного бота в администраторы канала с правом публикации/чтения сообщений!
* `BUFFER_API_KEY`: персональный токен Buffer (Buffer $\rightarrow$ Account Settings $\rightarrow$ Access & API).

### 4. Автоматическое определение подключённых соцсетей

DARK Reposter включает удобную утилиту для автоматического получения ID всех подключённых в Buffer соцсетей:

```bash
# Получить Organization ID:
python scripts/list_buffer_channels.py

# Укажите полученный BUFFER_ORGANIZATION_ID в .env и запустите скрипт повторно:
python scripts/list_buffer_channels.py
```

Скрипт выведет список всех каналов:
```text
Channels:
  bluesky    6aac099bea19ca0bde6a197a  DARK CITY _beta
  mastodon   6aabfef1ea19ca0bde6982f7  dark_city_bet
  twitter    6aabb377ea19ca0bde66938a  dark_city_beta
```

Скопируйте нужные ID в соответствующие переменные в `.env`:
```ini
BUFFER_CHANNEL_X=6aabb377ea19ca0bde66938a
BUFFER_CHANNEL_BLUESKY=6aac099bea19ca0bde6a197a
BUFFER_CHANNEL_MASTODON=6aabfef1ea19ca0bde6982f7
```

### 5. Тестовый запуск (Dry-Run)

По умолчанию можно протестировать работу без реальной публикации:
```bash
# В .env установите:
# DRY_RUN=true

python -m dark_reposter
```
Опубликуйте тестовый пост в канале — в логах отобразится парсинг, сборка альбома и варианты текста для каждой площадки.

Для боевой работы переключите в `.env`:
```ini
DRY_RUN=false
```

---

## ⚙️ Запуск как фоновый сервис (Systemd Daemon)

Чтобы репостер работал круглосуточно, не зависел от закрытия терминала и автоматически поднимался при перезагрузке машины:

```bash
# 1. Создаём директорию пользовательских юнитов
mkdir -p ~/.config/systemd/user

# 2. Копируем юнит-файл
cp systemd/dark-reposter.service ~/.config/systemd/user/

# 3. Перезагружаем демон и запускаем
systemctl --user daemon-reload
systemctl --user enable --now dark-reposter.service

# 4. Включаем linger (чтобы сервис продолжал работать после выхода пользователя)
loginctl enable-linger $USER
```

### Управление и скрипты:

В папке `scripts/` уже подготовлены вспомогательные команды:
* `./scripts/status.sh` — проверить статус сервиса и последние логи.
* `journalctl --user -u dark-reposter -f` — смотреть живой поток логов.
* `systemctl --user restart dark-reposter` — перезапуск сервиса.

---

## 📁 Структура проекта

```text
dark-reposter/
├── .env.example            # Образец конфигурационного файла
├── pyproject.toml          # Метаданные пакета Python
├── requirements.txt        # Зависимости проекта
├── run.sh                  # Исполняемый bash-скрипт для systemd
├── systemd/
│   └── dark-reposter.service # Юнит-файл для автозапуска
├── scripts/
│   ├── list_buffer_channels.py     # Инспектор каналов Buffer GraphQL
│   ├── resolve_telegram_channel.py # Утилита определения ID канала
│   ├── start.sh / status.sh / stop.sh
├── src/
│   └── dark_reposter/
│       ├── __init__.py
│       ├── __main__.py       # Точка входа
│       ├── config.py         # Валидация настроек и Pydantic-модели
│       ├── limits.py         # Лимиты длины текста по платформам
│       ├── media.py          # Обработка медиа и прямой доступ к Telegram CDN
│       ├── media_server.py   # Опциональный встроенный HTTP медиа-сервер
│       ├── models.py         # Датаклассы постов и медиа
│       ├── reposter.py       # Основной координатор кросспостинга
│       ├── storage.py        # SQLite хранилище истории
│       ├── telegram_app.py   # Обработчик aiogram long polling
│       ├── text_adapt.py     # Умная адаптация и сжатие текстов
│       └── publishers/
│           ├── base.py       # Базовый интерфейс издателя
│           └── buffer.py     # Реализация публикации через Buffer GraphQL
└── tests/
    └── test_text_adapt.py    # Модульные тесты адаптации текста
```

---

## 📜 Лицензия

Проект распространяется под открытой лицензией [MIT](LICENSE).  
Используйте, модифицируйте и делитесь контентом свободно!
