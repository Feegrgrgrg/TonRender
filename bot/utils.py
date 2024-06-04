from aiogram import Bot, Dispatcher, types
from config import CHANNEL_USERNAME, TOKEN
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiogram.utils.markdown as fmt
import sqlite3


bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect('users.db')
c = conn.cursor()


async def post_to_channel(message: str, username: str, user_id: int, amount: int):
    rounded_amount = round(amount, 2)
    try:
        if username:
            await bot.send_message(
    chat_id=CHANNEL_USERNAME, 
    text=fmt.text(
        f'''
Произведена оплата❗

<i>Пользователь:</i> <code>@{username}</code>
<i>ID:</i> <code>{user_id}</code>
<i>Сумма:</i> <code>{rounded_amount}$</code>
        '''
    ),
    parse_mode="HTML"
)


    except Exception as e:
        print(f"Не удалось отправить сообщение в канал: {e}")



async def check_captcha(input_text, captcha_text):
    return input_text.upper() == captcha_text.upper()


async def check_subscription(chat_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=chat_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False
    

async def is_admin(user_id: int):
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    return member.status in ['administrator', 'creator']



async def send_options_menu(message: types.Message):
    if await check_subscription(message.chat.id):
        c.execute("SELECT free_draws FROM users WHERE id=?", (message.chat.id,))
        free_draws = c.fetchone()[0]
        markup = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text="TON", callback_data='TON')
        button1 = InlineKeyboardButton(text="💵Пополнить баланс", callback_data='balance')
        markup.row(button)
        markup.row(button1)
        await message.answer(f'''
Количество отрисовок: {free_draws}

Выбери опцию ниже:''', reply_markup=markup)
    else:
        # Если подписка отсутствует, отправляем сообщение с предложением подписаться
        await message.answer('Пожалуйста, подпишитесь на наш канал, чтобы продолжить.🙏', reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton('Подписаться на канал', url=f'https://t.me/{CHANNEL_USERNAME[1:]}'),
            InlineKeyboardButton('Проверить подписку', callback_data='check_subscription')
        ))
