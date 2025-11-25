# bot.py - УЛУЧШЕННАЯ ВЕРСИЯ
import asyncio
import uuid
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from google_sync import read_objects, read_bookings, append_booking, delete_booking, get_user_bookings, \
    get_all_active_bookings
from airbnb_sync import sync_airbnb_to_google, sync_google_to_airbnb
import config

bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher()


# ===== КЛАВИАТУРЫ =====
def main_keyboard():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Список объектов"), KeyboardButton(text="📅 Мои брони")],
            [KeyboardButton(text="🔄 Синхронизировать"), KeyboardButton(text="📊 Все брони")]
        ],
        resize_keyboard=True
    )
    return keyboard


def objects_keyboard():
    """Клавиатура с объектами"""
    objects = read_objects()
    keyboard = InlineKeyboardBuilder()

    for obj in objects:
        keyboard.button(
            text=f"🏠 {obj['name']} ({obj['object_id']})",
            callback_data=f"object_{obj['object_id']}"
        )

    keyboard.button(text="« Назад в меню", callback_data="back_to_main")
    keyboard.adjust(1)
    return keyboard.as_markup()


def my_bookings_keyboard(user_id):
    """Клавиатура с бронями пользователя"""
    user_bookings = get_user_bookings(user_id)
    keyboard = InlineKeyboardBuilder()

    if not user_bookings:
        keyboard.button(text="🎯 Забронировать сейчас", callback_data="book_now")
    else:
        for booking in user_bookings:
            display_text = f"🗓 {booking['object_id']} ({booking['start']})"
            keyboard.button(
                text=display_text,
                callback_data=f"manage_{booking['booking_id']}"
            )

    keyboard.button(text="« Назад в меню", callback_data="back_to_main")
    keyboard.adjust(1)
    return keyboard.as_markup()


def all_bookings_keyboard():
    """Клавиатура со всеми бронированиями (для отладки)"""
    all_bookings = get_all_active_bookings()
    keyboard = InlineKeyboardBuilder()

    if not all_bookings:
        keyboard.button(text="📭 Нет активных броней", callback_data="none")
    else:
        for booking in all_bookings[:10]:  # Ограничиваем 10 бронями
            user_info = f"👤{booking.get('created_by', '?')}"
            display_text = f"🏠{booking['object_id']} {booking['start']} {user_info}"
            if len(display_text) > 30:
                display_text = display_text[:27] + "..."

            keyboard.button(
                text=display_text,
                callback_data=f"view_{booking['booking_id']}"
            )

    keyboard.button(text="« Назад в меню", callback_data="back_to_main")
    keyboard.adjust(1)
    return keyboard.as_markup()


def booking_management_keyboard(booking_id):
    """Кнопки управления конкретной броней"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Удалить бронь", callback_data=f"delete_confirm_{booking_id}")
    keyboard.button(text="« Назад к моим броням", callback_data="back_to_my_bookings")
    keyboard.adjust(1)
    return keyboard.as_markup()


def delete_confirmation_keyboard(booking_id):
    """Подтверждение удаления"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Да, удалить", callback_data=f"delete_yes_{booking_id}")
    keyboard.button(text="❌ Нет, отмена", callback_data=f"delete_no_{booking_id}")
    keyboard.adjust(2)
    return keyboard.as_markup()


# ===== ФУНКЦИИ =====
def is_available(object_id, start, end):
    """Проверяет доступность дат"""
    bookings = read_bookings()
    for b in bookings:
        if (str(b.get('object_id', '')).strip() == str(object_id).strip() and
                str(b.get('status', '')).strip().lower() == 'booked' and
                not (end <= b['start'] or start >= b['end'])):
            return False
    return True


def create_booking(object_id, start, end, user_id):
    """Создает новое бронирование"""
    booking_id = f"bk_{uuid.uuid4().hex[:8]}"
    booking_data = {
        'booking_id': booking_id,
        'object_id': object_id,
        'start': start,
        'end': end,
        'status': 'booked',
        'source': 'bot',
        'created_by': str(user_id)
    }
    if append_booking(booking_data):
        return booking_id
    return None


def format_booking(booking):
    """Форматирует бронирование для красивого отображения"""
    source_emoji = "🤖" if booking.get('source') == 'bot' else "🏠"
    user_info = f"👤 {booking.get('created_by', 'Неизвестно')}"

    return (f"{source_emoji} *{booking['object_id']}*\n"
            f"📅 *{booking['start']} → {booking['end']}*\n"
            f"🆔 `{booking['booking_id']}`\n"
            f"{user_info}\n"
            f"━━━━━━━━━━━━━━━━")


def format_object(obj):
    """Форматирует объект для красивого отображения"""
    has_calendar = "✅" if obj.get('calendar_url') else "❌"
    return (f"🏠 *{obj['name']}*\n"
            f"🆔 `{obj['object_id']}`\n"
            f"📍 {obj.get('type', 'Не указан')}\n"
            f"📅 Синхронизация с Airbnb: {has_calendar}\n"
            f"━━━━━━━━━━━━━━━━")


# ===== КОМАНДЫ =====
@dp.message(Command(commands=['start', 'help']))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎯 *Бот управления бронированиями*\n\n"
        "*Основные команды:*\n"
        "🏠 Список объектов - посмотреть доступные объекты\n"
        "📅 Мои брони - управление вашими бронированиями\n"
        "🔄 Синхронизировать - обновить данные с Airbnb\n"
        "📊 Все брони - посмотреть все активные брони\n\n"
        "*Быстрые команды:*\n"
        "/book <объект> <начало> <конец> - быстрая бронь\n"
        "/check <объект> <начало> <конец> - проверить даты\n"
        "/debug - отладочная информация",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(F.text == "🏠 Список объектов")
async def list_objects(message: types.Message):
    objects = read_objects()

    if not objects:
        await message.answer("❌ Нет доступных объектов")
        return

    text = "🏠 *Доступные объекты:*\n\n"
    for obj in objects:
        text += format_object(obj) + "\n"

    text += "\n🎯 Выберите объект для бронирования:"

    await message.answer(text, reply_markup=objects_keyboard(), parse_mode="Markdown")


@dp.message(F.text == "📅 Мои брони")
async def my_bookings_cmd(message: types.Message):
    user_bookings = get_user_bookings(message.from_user.id)

    if not user_bookings:
        await message.answer(
            "📭 *У вас пока нет активных бронирований*\n\n"
            "🎯 Чтобы забронировать, нажмите «🏠 Список объектов»\n\n"
            f"💡 *Ваш ID:* `{message.from_user.id}`",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        return

    text = f"📅 *Ваши активные бронирования ({len(user_bookings)}):*\n\n"
    for booking in user_bookings:
        text += format_booking(booking) + "\n"

    text += "\n🎯 Выберите бронь для управления:"

    await message.answer(
        text,
        reply_markup=my_bookings_keyboard(message.from_user.id),
        parse_mode="Markdown"
    )


@dp.message(F.text == "📊 Все брони")
async def all_bookings_cmd(message: types.Message):
    all_bookings = get_all_active_bookings()

    if not all_bookings:
        await message.answer("📭 Нет активных бронирований в системе")
        return

    text = f"📊 *Все активные бронирования ({len(all_bookings)}):*\n\n"
    for booking in all_bookings[:15]:  # Ограничиваем вывод
        text += format_booking(booking) + "\n"

    if len(all_bookings) > 15:
        text += f"\n... и еще {len(all_bookings) - 15} броней"

    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "🔄 Синхронизировать")
async def sync_cmd(message: types.Message):
    await message.answer("🔄 Синхронизируем данные с Airbnb...")
    sync_airbnb_to_google()
    await message.answer("✅ Синхронизация завершена!", reply_markup=main_keyboard())


# ===== ИНЛАЙН КНОПКИ =====
@dp.callback_query(F.data.startswith("object_"))
async def object_selected(callback: types.CallbackQuery):
    object_id = callback.data.replace("object_", "")
    objects = read_objects()

    obj = next((o for o in objects if o['object_id'] == object_id), None)
    if not obj:
        await callback.answer("❌ Объект не найден")
        return

    text = (f"🎯 *Выбран объект:* {obj['name']}\n"
            f"🆔 `{object_id}`\n\n"
            f"*Для бронирования используйте:*\n"
            f"`/book {object_id} 2024-01-15 2024-01-20`\n\n"
            f"*Для проверки доступности:*\n"
            f"`/check {object_id} 2024-01-15 2024-01-20`")

    await callback.message.edit_text(text, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("manage_"))
async def manage_booking(callback: types.CallbackQuery):
    booking_id = callback.data.replace("manage_", "")
    bookings = read_bookings()

    booking = next((b for b in bookings if b['booking_id'] == booking_id), None)
    if not booking:
        await callback.answer("❌ Бронь не найдена")
        return

    text = (f"📋 *Управление бронированием*\n\n"
            f"{format_booking(booking)}\n\n"
            f"Выберите действие:")

    await callback.message.edit_text(
        text,
        reply_markup=booking_management_keyboard(booking_id),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("delete_confirm_"))
async def delete_confirm(callback: types.CallbackQuery):
    booking_id = callback.data.replace("delete_confirm_", "")
    bookings = read_bookings()

    booking = next((b for b in bookings if b['booking_id'] == booking_id), None)
    if not booking:
        await callback.answer("❌ Бронь не найдена")
        return

    text = (f"❓ *Подтверждение удаления*\n\n"
            f"Вы действительно хотите удалить бронь?\n\n"
            f"{format_booking(booking)}\n\n"
            f"⚠️ *Это действие нельзя отменить!*")

    await callback.message.edit_text(
        text,
        reply_markup=delete_confirmation_keyboard(booking_id),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("delete_yes_"))
async def delete_yes(callback: types.CallbackQuery):
    booking_id = callback.data.replace("delete_yes_", "")

    # Получаем информацию о брони перед удалением
    bookings = read_bookings()
    booking = next((b for b in bookings if b['booking_id'] == booking_id), None)

    if not booking:
        await callback.answer("❌ Бронь не найдена")
        return

    object_id = booking['object_id']

    # Удаляем бронь
    if delete_booking(booking_id):
        await callback.answer("✅ Бронь удалена")

        # Обновляем Airbnb
        sync_google_to_airbnb(object_id)

        text = (f"✅ *Бронь успешно удалена!*\n\n"
                f"🏠 *Объект:* {object_id}\n"
                f"📅 *Даты:* {booking['start']} → {booking['end']}\n"
                f"🆔 *ID:* `{booking_id}`\n\n"
                f"📱 *Airbnb* будет обновлен в течение часа")

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardBuilder()
            .button(text="📅 К моим броням", callback_data="back_to_my_bookings")
            .button(text="🏠 В главное меню", callback_data="back_to_main")
            .adjust(1)
            .as_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Ошибка удаления")
        await callback.message.edit_text(
            "❌ *Не удалось удалить бронь*\n\n"
            "Попробуйте позже или обратитесь к администратору",
            reply_markup=booking_management_keyboard(booking_id),
            parse_mode="Markdown"
        )


@dp.callback_query(F.data.startswith("delete_no_"))
async def delete_no(callback: types.CallbackQuery):
    booking_id = callback.data.replace("delete_no_", "")
    await callback.answer("❌ Удаление отменено")
    await manage_booking(callback)


@dp.callback_query(F.data == "back_to_my_bookings")
async def back_to_my_bookings(callback: types.CallbackQuery):
    user_bookings = get_user_bookings(callback.from_user.id)

    if not user_bookings:
        await callback.message.edit_text(
            "📭 *У вас пока нет активных бронирований*\n\n"
            "🎯 Чтобы забронировать, нажмите «🏠 Список объектов»",
            reply_markup=main_keyboard(),
            parse_mode="Markdown"
        )
        return

    text = f"📅 *Ваши активные бронирования ({len(user_bookings)}):*\n\n"
    for booking in user_bookings:
        text += format_booking(booking) + "\n"

    text += "\n🎯 Выберите бронь для управления:"

    await callback.message.edit_text(
        text,
        reply_markup=my_bookings_keyboard(callback.from_user.id),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await start_cmd(callback.message)


@dp.callback_query(F.data == "book_now")
async def book_now(callback: types.CallbackQuery):
    await list_objects(callback.message)


# ===== ТЕКСТОВЫЕ КОМАНДЫ =====
@dp.message(Command(commands=['debug']))
async def debug_cmd(message: types.Message):
    """Отладочная информация"""
    user_bookings = get_user_bookings(message.from_user.id)
    all_bookings = get_all_active_bookings()

    text = (f"🐛 *Отладочная информация*\n\n"
            f"👤 *Ваш ID:* `{message.from_user.id}`\n"
            f"📅 *Ваших броней:* {len(user_bookings)}\n"
            f"🏠 *Всего активных броней:* {len(all_bookings)}\n\n"
            f"*Ваши брони:*\n")

    for i, booking in enumerate(user_bookings, 1):
        text += f"{i}. {booking['object_id']} {booking['start']}-{booking['end']}\n"

    if not user_bookings:
        text += "Нет бронирований\n"

    text += f"\n*created_by в ваших бронях:*\n"
    for booking in user_bookings:
        text += f"- '{booking.get('created_by')}' (тип: {type(booking.get('created_by'))})\n"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command(commands=['check']))
async def check_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer(
            "❌ *Неверный формат*\n\n"
            "✅ *Правильно:*\n"
            "`/check villa_1 2024-01-15 2024-01-20`",
            parse_mode="Markdown"
        )
        return

    _, object_id, start, end = parts

    if is_available(object_id, start, end):
        await message.answer(
            f"✅ *{object_id} СВОБОДЕН!*\n\n"
            f"📅 *Период:* {start} - {end}\n\n"
            f"🎯 *Забронировать:*\n"
            f"`/book {object_id} {start} {end}`",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"❌ *{object_id} ЗАНЯТ*\n\n"
            f"📅 *Период:* {start} - {end}\n\n"
            f"💡 Попробуйте другие даты",
            parse_mode="Markdown"
        )


@dp.message(Command(commands=['book']))
async def book_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer(
            "❌ *Неверный формат*\n\n"
            "✅ *Правильно:*\n"
            "`/book villa_1 2024-01-15 2024-01-20`",
            parse_mode="Markdown"
        )
        return

    _, object_id, start, end = parts

    if not is_available(object_id, start, end):
        await message.answer(
            "❌ *Эти даты уже заняты*\n\n"
            "💡 Используйте `/check` чтобы найти свободные даты",
            parse_mode="Markdown"
        )
        return

    booking_id = create_booking(object_id, start, end, message.from_user.id)

    if not booking_id:
        await message.answer(
            "❌ *Ошибка создания брони*\n\n"
            "Попробуйте позже или обратитесь к администратору",
            parse_mode="Markdown"
        )
        return

    # Обновляем Airbnb
    gist_url = sync_google_to_airbnb(object_id)

    if gist_url:
        await message.answer(
            f"🎉 *Бронь создана!*\n\n"
            f"🏠 *Объект:* {object_id}\n"
            f"📅 *Период:* {start} - {end}\n"
            f"🆔 *ID брони:* `{booking_id}`\n\n"
            f"📱 *Airbnb* получит обновления в течение часа",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(
            f"🎉 *Бронь создана локально!*\n\n"
            f"🏠 *Объект:* {object_id}\n"
            f"📅 *Период:* {start} - {end}\n"
            f"🆔 *ID брони:* `{booking_id}`\n\n"
            f"⚠️ *Airbnb* не обновлен\n"
            f"💡 Используйте кнопку «🔄 Синхронизировать»",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )


@dp.message(Command(commands=['sync']))
async def sync_command(message: types.Message):
    await sync_cmd(message)


@dp.message(Command(commands=['force_sync']))
async def force_sync_cmd(message: types.Message):
    """Принудительная синхронизация с Airbnb"""
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer(
            "❌ *Неверный формат*\n\n"
            "✅ *Правильно:*\n"
            "`/force_sync villa_1`",
            parse_mode="Markdown"
        )
        return

    object_id = parts[1]

    await message.answer(f"🔄 Принудительная синхронизация {object_id} с Airbnb...")

    from airbnb_sync import sync_google_to_airbnb
    gist_url = sync_google_to_airbnb(object_id)

    if gist_url:
        await message.answer(
            f"✅ *Синхронизация выполнена!*\n\n"
            f"🏠 *Объект:* {object_id}\n"
            f"🔗 *Gist URL:* {gist_url}\n\n"
            f"💡 *Что делать дальше:*\n"
            f"1. Скопируйте ссылку выше\n"
            f"2. В Airbnb: Календарь → Настройки календаря\n"
            f"3. Удалите старый календарь\n"
            f"4. Добавьте новый с этой ссылкой\n"
            f"5. Airbnb обновит данные в течение 2 часов",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ *Не удалось синхронизировать*\n\n"
            "Проверьте:\n"
            "• GitHub токен в airbnb_sync.py\n"
            "• Наличие броней для этого объекта\n"
            "• Интернет соединение",
            parse_mode="Markdown"
        )

# Запуск бота
async def main():
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())