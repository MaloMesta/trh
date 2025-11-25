# airbnb_sync.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import requests
from icalendar import Calendar, Event
from datetime import datetime, date, timedelta
import time
import uuid
from google_sync import read_objects, read_bookings, append_booking, delete_booking
import config

# 🔑 ЗАМЕНИ НА СВОЙ ТОКЕН
GITHUB_TOKEN = "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"
GIST_ID = "66d492660f311f3029f0f74a700fb2ad"


def create_github_gist(object_id, ical_content):
    """Создает или обновляет Gist на GitHub"""
    global GIST_ID

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "public": True,
        "description": f"Booking Calendar for {object_id}",
        "files": {
            f"{object_id}.ics": {
                "content": ical_content
            }
        }
    }

    try:
        if GIST_ID:
            url = f"https://api.github.com/gists/{GIST_ID}"
            response = requests.patch(url, headers=headers, json=data)
        else:
            url = "https://api.github.com/gists"
            response = requests.post(url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            result = response.json()
            GIST_ID = result['id']
            raw_url = result['files'][f'{object_id}.ics']['raw_url']
            print(f"✅ Gist обновлен: {raw_url}")
            return raw_url
        else:
            print(f"❌ Ошибка GitHub: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"❌ Ошибка обновления Gist: {e}")
        return None


def validate_booking_dates(start_date_str, end_date_str):
    """Проверяет и исправляет даты бронирования"""
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)

        # Проверяем что конечная дата не раньше начальной
        if end_date <= start_date:
            print(f"⚠️ Исправляем даты: {start_date} - {end_date} → {start_date} - {start_date + timedelta(days=1)}")
            end_date = start_date + timedelta(days=1)

        return start_date, end_date
    except Exception as e:
        print(f"❌ Ошибка валидации дат {start_date_str}-{end_date_str}: {e}")
        return None, None


def generate_ical_for_airbnb(object_id):
    """Генерирует iCal специально для Airbnb с проверкой дат"""
    try:
        bookings = read_bookings()
        object_bookings = [b for b in bookings if str(b.get('object_id', '')).strip() == str(object_id).strip() and str(
            b.get('status', '')).strip().lower() == 'booked']

        print(f"📊 Найдено {len(object_bookings)} броней для {object_id}")

        # Создаем календарь
        cal = Calendar()
        cal.add('prodid', '-//Airbnb//NONSGML//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', f'Calendar for {object_id}')
        cal.add('x-wr-timezone', 'UTC')

        valid_events_count = 0

        for booking in object_bookings:
            # ВАЖНО: Проверяем и исправляем даты
            start_date, end_date = validate_booking_dates(booking['start'], booking['end'])

            if not start_date or not end_date:
                print(f"❌ Пропускаем бронь с невалидными датами: {booking}")
                continue

            # Проверяем что бронь в будущем (Airbnb может игнорировать прошлые даты)
            if end_date < date.today():
                print(f"⚠️ Пропускаем прошедшую бронь: {start_date} - {end_date}")
                continue

            event = Event()
            event.add('summary', 'UNAVAILABLE')
            event.add('dtstart', start_date)
            event.add('dtend', end_date)
            event.add('dtstamp', datetime.now())
            event.add('uid', f"{booking['booking_id']}@booking-bot.com")
            event.add('created', datetime.now())
            event.add('last-modified', datetime.now())
            event.add('sequence', 0)
            event.add('status', 'CONFIRMED')
            event.add('transp', 'OPAQUE')

            event.add('description',
                      f"Booked via internal system. "
                      f"Booking ID: {booking['booking_id']}")

            cal.add_component(event)
            valid_events_count += 1
            print(f"✅ Добавлено событие: {start_date} - {end_date} (ID: {booking['booking_id']})")

        if valid_events_count == 0:
            print(f"ℹ️ Нет валидных броней для {object_id}, создаю пустой календарь")
            # Добавляем тестовое событие в будущем
            event = Event()
            future_date = date.today() + timedelta(days=30)
            event.add('summary', 'UNAVAILABLE - SAMPLE')
            event.add('dtstart', future_date)
            event.add('dtend', future_date + timedelta(days=1))
            event.add('dtstamp', datetime.now())
            event.add('uid', 'sample-event@booking-bot')
            event.add('created', datetime.now())
            event.add('status', 'CONFIRMED')
            event.add('transp', 'OPAQUE')
            cal.add_component(event)
            valid_events_count = 1

        ical_content = cal.to_ical().decode('utf-8')
        print(f"✅ Сгенерирован iCal с {valid_events_count} валидными событиями")
        return ical_content

    except Exception as e:
        print(f"❌ Ошибка генерации iCal: {e}")
        return None


def sync_google_to_airbnb(object_id):
    """Синхронизирует Google Sheets → Airbnb через GitHub Gist"""
    print(f"🔄 Синхронизация Google → Airbnb для {object_id}...")

    # Генерируем свежий iCal
    ical_content = generate_ical_for_airbnb(object_id)

    if not ical_content:
        print("❌ Не удалось сгенерировать iCal")
        return None

    # Сохраняем локально для проверки
    try:
        with open(f"{object_id}_debug.ics", "w", encoding='utf-8') as f:
            f.write(ical_content)
        print(f"💾 Локальная копия сохранена: {object_id}_debug.ics")
    except Exception as e:
        print(f"⚠️ Не удалось сохранить локальную копию: {e}")

    # Обновляем GitHub Gist
    gist_url = create_github_gist(object_id, ical_content)

    if gist_url:
        print(f"✅ Gist обновлен: {gist_url}")
        return gist_url
    else:
        print("❌ Не удалось обновить Gist")
        return None


# Остальные функции без изменений
def fetch_airbnb_calendar(calendar_url):
    """Получает календарь Airbnb"""
    try:
        print(f"📥 Загружаем календарь: {calendar_url}")
        response = requests.get(calendar_url, timeout=10)
        response.raise_for_status()

        cal = Calendar.from_ical(response.content)
        events = []

        for component in cal.walk():
            if component.name == "VEVENT":
                dtstart = component.get('dtstart').dt
                dtend = component.get('dtend').dt

                if isinstance(dtstart, datetime):
                    dtstart = dtstart.date()
                if isinstance(dtend, datetime):
                    dtend = dtend.date()

                events.append({
                    "start": dtstart.isoformat(),
                    "end": dtend.isoformat()
                })

        print(f"📅 Найдено {len(events)} событий")
        return events
    except Exception as e:
        print(f"❌ Ошибка загрузки календаря: {e}")
        return []


def sync_airbnb_to_google():
    """Синхронизирует Airbnb -> Google Sheets"""
    print("🔄 Синхронизация Airbnb -> Google Sheets...")

    objects = read_objects()
    imported_count = 0

    for obj in objects:
        calendar_url = obj.get('calendar_url')
        if not calendar_url:
            continue

        object_id = obj['object_id']
        print(f"🔍 Проверяем {object_id}...")

        airbnb_events = fetch_airbnb_calendar(calendar_url)
        existing_bookings = read_bookings()

        for event in airbnb_events:
            already_exists = any(
                str(b.get('object_id', '')).strip() == str(object_id).strip() and
                b['start'] == event['start'] and
                b['end'] == event['end']
                for b in existing_bookings
            )

            if not already_exists:
                new_booking = {
                    'booking_id': f"airbnb_{uuid.uuid4().hex[:8]}",
                    'object_id': object_id,
                    'start': event['start'],
                    'end': event['end'],
                    'status': 'booked',
                    'source': 'airbnb',
                    'created_by': 'airbnb_sync'
                }
                if append_booking(new_booking):
                    imported_count += 1
                    print(f"✅ Добавлено бронирование: {object_id} {event['start']} - {event['end']}")

    if imported_count > 0:
        print(f"✅ Импортировано {imported_count} бронирований из Airbnb")
    else:
        print("ℹ️ Новых бронирований из Airbnb не найдено")