# Booking Bot MVP (minimal)
Простая версия бота для сотрудников: проверка и закрытие дат, синхронизация с Google Sheets и импорт/экспорт iCal.

Файлы:
- bot.py             — минимальный Telegram bot (aiogram) с командами проверки и закрытия дат
- config.py          — конфиг (токены, IDs) — **заполни своими значениями**
- google_sync.py     — функции чтения/записи Google Sheets (gspread)
- calendar_sync.py   — простая функция для чтения iCal (icalendar/ics)
- business_logic.py  — логика: проверка доступности, запись брони
- models.py          — простые модели (в памяти) и helper для сохранения в CSV/Google
- requirements.txt   — pip зависимости
- sample_google_sheet.csv — пример структуры Google Sheet (можно импортировать)

Быстрый старт (локально):
1. Установи зависимости: `pip install -r requirements.txt`
2. Создай Google Service Account и скачай JSON — укажи путь в config.py (SERVICE_ACCOUNT_FILE)
3. Создай Google Sheet и укажи его ID в config.py (SHEET_ID)
4. Заполни бот токен в config.py (TELEGRAM_TOKEN)
5. Запусти локально: `python bot.py`

Дальше — адаптация под reg.ru (VPS) описана в разделе Deploy.
