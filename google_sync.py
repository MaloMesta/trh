# google_sync.py - ОБНОВЛЕННАЯ ВЕРСИЯ
import gspread
from google.oauth2.service_account import Credentials
import config

SCOPE = ['https://www.googleapis.com/auth/spreadsheets']


def get_client():
    creds = Credentials.from_service_account_file(config.SERVICE_ACCOUNT_FILE, scopes=SCOPE)
    return gspread.authorize(creds)


def read_bookings():
    """Читает все бронирования"""
    try:
        gc = get_client()
        sh = gc.open_by_key(config.SHEET_ID)
        ws = sh.worksheet('bookings')
        return ws.get_all_records()
    except Exception as e:
        print(f"❌ Ошибка чтения бронирований: {e}")
        return []


def read_objects():
    """Читает все объекты"""
    try:
        gc = get_client()
        sh = gc.open_by_key(config.SHEET_ID)
        ws = sh.worksheet('objects')
        return ws.get_all_records()
    except Exception as e:
        print(f"❌ Ошибка чтения объектов: {e}")
        return []


def append_booking(booking_data):
    """Добавляет новое бронирование"""
    try:
        gc = get_client()
        sh = gc.open_by_key(config.SHEET_ID)
        ws = sh.worksheet('bookings')
        ws.append_row([
            booking_data.get('booking_id', ''),
            booking_data.get('object_id', ''),
            booking_data.get('start', ''),
            booking_data.get('end', ''),
            booking_data.get('status', 'booked'),
            booking_data.get('source', 'internal'),
            booking_data.get('created_by', '')
        ])
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления брони: {e}")
        return False


def delete_booking(booking_id):
    """Удаляет бронирование из таблицы"""
    try:
        gc = get_client()
        sh = gc.open_by_key(config.SHEET_ID)
        ws = sh.worksheet('bookings')

        # Находим строку с booking_id
        records = ws.get_all_records()
        for i, record in enumerate(records, start=2):  # start=2 т.к. 1 строка - заголовки
            if str(record.get('booking_id', '')).strip() == str(booking_id).strip():
                # Удаляем строку
                ws.delete_rows(i)
                print(f"✅ Бронь {booking_id} удалена из строки {i}")
                return True

        print(f"❌ Бронь {booking_id} не найдена")
        return False

    except Exception as e:
        print(f"❌ Ошибка удаления брони: {e}")
        return False


def get_user_bookings(user_id):
    """Получает бронирования конкретного пользователя"""
    bookings = read_bookings()
    user_bookings = []

    for booking in bookings:
        # Приводим к строке для сравнения (user_id может быть числом или строкой в таблице)
        created_by = str(booking.get('created_by', '')).strip()
        user_id_str = str(user_id).strip()
        status = str(booking.get('status', '')).strip().lower()

        if created_by == user_id_str and status == 'booked':
            user_bookings.append(booking)

    print(f"🔍 Найдено {len(user_bookings)} броней для пользователя {user_id}")
    return user_bookings


def get_all_active_bookings():
    """Получает все активные бронирования (для отладки)"""
    bookings = read_bookings()
    active_bookings = [b for b in bookings if str(b.get('status', '')).strip().lower() == 'booked']
    return active_bookings