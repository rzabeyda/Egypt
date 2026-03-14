# 🏖️ Egypt Tour Bot

Телеграм бот — горящие туры в Египет из Таллина.

## Операторы
| Оператор | Сайт |
|----------|------|
| Novatours | novatours.ee |
| TEZ Tour | teztour.ee |
| Coral Travel | coral.ee |
| Join Up | joinup.eu |

## Фильтры
- ✈️ Вылет: **Таллин (TLL)**
- 🏖 Направление: **Хургада / Шарм-эль-Шейх**
- 💰 До **400€ / чел**
- 🌙 Минимум **7 ночей**
- 🏨 Только хорошие отели (Jazz, Sunrise, Albatros, Steigenberger, Rixos, Hilton…)
- ⏱ Проверка каждые **30 минут**

---

## 🚀 Установка

```bash
# 1. Распакуй в C:\Egypt\egypt_bot\

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Запусти бота
python bot.py

# 4. Напиши боту /myid — получишь свой chat_id
# 5. Вставь chat_id в config.py → ALLOWED_USERS = [ВАШ_ID]
# 6. Перезапусти бота и пиши /start
```

## Команды
| Команда | Описание |
|---------|----------|
| `/start` | Подписаться |
| `/stop` | Отписаться |
| `/check` | Проверить прямо сейчас |
| `/status` | Статус бота |
| `/last` | Последние 5 туров |
| `/myid` | Узнать свой chat_id |

## Структура
```
egypt_bot/
├── bot.py           ← ЗАПУСКАТЬ
├── config.py        ← настройки
├── database.py
├── filters.py
├── formatter.py
├── requirements.txt
├── scrapers/
│   ├── novatours.py
│   ├── teztour.py
│   ├── coral.py
│   └── joinup.py
├── data/            ← создаётся автоматически
└── logs/            ← создаётся автоматически
```

## Настройка фильтров (config.py)
```python
MAX_PRICE_EUR = 400   # цена за человека
MIN_NIGHTS    = 7     # минимум ночей

# Добавить отель в список хороших:
GOOD_HOTELS = ["jazz", "sunrise", ...]
```
