import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
import db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class AdminStates(StatesGroup):
    waiting_config = State()  # админ вводит конфиг для конкретного юзера

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def user_request_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Запросить доступ к VPN", callback_data="request_access")]
    ])

def admin_decision_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выдать доступ", callback_data=f"grant:{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}"),
        ]
    ])

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Это бот для получения доступа к VPN.\n\n"
        "Нажми кнопку ниже, чтобы отправить заявку. "
        "После проверки администратор вручную вышлет тебе конфиг прямо сюда.",
        reply_markup=user_request_keyboard()
    )

@dp.callback_query(F.data == "request_access")
async def on_request_access(callback: CallbackQuery):
    user = callback.from_user
    db.add_or_update_request(user.id, user.username or "", user.full_name)

    await callback.message.edit_text(
        "✅ Заявка отправлена! Ожидай — администратор свяжется с тобой в этом чате."
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📥 Новая заявка на VPN\n\n"
                f"Имя: {user.full_name}\n"
                f"Username: @{user.username if user.username else '—'}\n"
                f"ID: {user.id}",
                reply_markup=admin_decision_keyboard(user.id)
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    await callback.answer()

@dp.callback_query(F.data.startswith("grant:"))
async def on_grant(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    target_id = int(callback.data.split(":")[1])
    await state.update_data(target_id=target_id)
    await state.set_state(AdminStates.waiting_config)

    await callback.message.answer(
        f"Отправь конфиг/инструкцию для пользователя {target_id} следующим сообщением "
        f"(текст, файл или фото — что угодно). Я перешлю это ему."
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("reject:"))
async def on_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return

    target_id = int(callback.data.split(":")[1])
    db.set_status(target_id, "rejected")

    try:
        await bot.send_message(target_id, "К сожалению, твоя заявка на доступ к VPN отклонена.")
    except Exception:
        pass

    await callback.message.edit_text(callback.message.text + "\n\n❌ Отклонено")
    await callback.answer("Заявка отклонена")

@dp.message(AdminStates.waiting_config)
async def on_admin_sends_config(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target_id = data.get("target_id")

    try:
        await message.copy_to(target_id)
        await bot.send_message(
            target_id,
            "👆 Твой доступ к VPN выдан. Если что-то не работает — напиши сюда."
        )
        db.set_status(target_id, "active")
        await message.answer(f"Готово, отправлено пользователю {target_id}.")
    except Exception as e:
        await message.answer(f"Не удалось отправить пользователю {target_id}: {e}")

    await state.clear()

@dp.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = db.list_users()
    if not rows:
        await message.answer("Заявок пока нет.")
        return

    lines = []
    for user_id, username, full_name, status, requested_at in rows:
        uname = f"@{username}" if username else "—"
        lines.append(f"{user_id} | {full_name} | {uname} | {status} | {requested_at}")

    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3500] + "\n… (список обрезан)"
    await message.answer(f"Всего заявок: {len(rows)}\n\n{text}")

@dp.message(Command("pending"))
async def cmd_pending(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = db.list_users(status="pending")
    if not rows:
        await message.answer("Нет заявок в ожидании.")
        return

    for user_id, username, full_name, status, requested_at in rows:
        uname = f"@{username}" if username else "—"
        await message.answer(
            f"ID: {user_id}\nИмя: {full_name}\nUsername: {uname}",
            reply_markup=admin_decision_keyboard(user_id)
        )

@dp.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /revoke <user_id>")
        return

    target_id = int(parts[1])
    db.set_status(target_id, "revoked")
    await message.answer(f"Доступ пользователя {target_id} помечен как отозванный.")
    try:
        await bot.send_message(target_id, "Твой доступ к VPN был отозван администратором.")
    except Exception:
        pass

async def main():
    db.init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
      
