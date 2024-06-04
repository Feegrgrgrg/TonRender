from aiogram import types, Bot
import sqlite3
from database import add_user_to_db
from aiogram import Dispatcher
from config import TOKEN
from bot import is_admin, send_options_menu, post_to_channel
from bot import generate_random_text, check_captcha
from datetime import datetime, timedelta
from captcha.image import ImageCaptcha
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import check_subscription
from config import CHANNEL_USERNAME
from bot import main2, create_invoice, check_invoice_payment
from bot import abbreviations
from PIL import Image, ImageFont, ImageDraw
import os
import aiogram.utils.markdown as fmt



bot = Bot(token=TOKEN)
dp = Dispatcher(bot)



conn = sqlite3.connect('users.db')
c = conn.cursor()

user_captcha = {}
user_data = {}

@dp.message_handler(commands=['admin'])
async def admin_command(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    if await is_admin(user_id):
        if len(args) == 1:

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, free_draws FROM users')
            users = cursor.fetchall()
            conn.close()

            if users:
                response = "Используй команду:\n /admin  id  кол-во отрисовок \n"

            else:
                response = "No users found."

            await message.reply(response)
        elif len(args) == 3:
            try:
                user_id = int(args[1])
                draws_to_add = int(args[2])
            except ValueError:
                await message.reply("Использование: /admin id кол-во отрисовок")
                return

            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            cursor.execute('SELECT username, free_draws FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()

            if user:
                new_free_draws = user[1] + draws_to_add
                cursor.execute('UPDATE users SET free_draws = ? WHERE id = ?', (new_free_draws, user_id))
                conn.commit()
                conn.close()
                await message.reply(f"Пользователь {user[0]} имеет {new_free_draws} отрисовок")
            else:
                conn.close()
                await message.reply(f"Пользователь с ID {user_id} не найден.")
        else:
            await message.reply("Использование: /admin id кол-во отрисовок")
    else:
        await bot.send_message(message.chat.id, 'У вас нет прав для выполнения этого действия. /start')
        
        
        
@dp.message_handler(commands=['draws'])
async def start(message: types.Message):
    user = message.from_user
    
    # Получаем количество бесплатных отрисовок пользователя из базы данных
    c.execute("SELECT free_draws FROM users WHERE id=?", (message.chat.id,))
    free_draws = c.fetchone()[0]
    
    c.execute("SELECT last_scan_time FROM users WHERE id=?", (user.id,))
    last_scan_time_str = c.fetchone()[0]

    if last_scan_time_str:
        last_scan_time = datetime.fromisoformat(last_scan_time_str)
    else:
        last_scan_time = None

    # Получение текущего времени
    current_time = datetime.now()

    if last_scan_time is None or (current_time - last_scan_time) >= timedelta(days=1):
        # Обновление времени сканирования
        last_scan_time = current_time
        c.execute("UPDATE users SET last_scan_time=? WHERE id=?", (last_scan_time.isoformat(), user.id))
        conn.commit()
        print("Время сканирования обновлено успешно.")
    else:
        print("Время сканирования уже обновлено за последние 24 часа.")
    
    rounded_last_scan_time = last_scan_time.strftime('%H:%M:%S')
    await message.answer(f'''
У вас доступно {free_draws} отрисовок.

Бесплатная отрисовка завтра в: {rounded_last_scan_time}''')
    
    
    
@dp.message_handler(commands=['start'])
async def start1(message: types.Message):
    user = message.from_user

    # Проверяем, есть ли пользователь в базе данных
    c.execute("SELECT id FROM users WHERE id=?", (user.id,))
    user_in_db = c.fetchone()

    if user_in_db:
        c.execute("SELECT free_draws, last_scan_time FROM users WHERE id=?", (user.id,))
        user_data = c.fetchone()
        
        if user_data:
            free_draws, last_scan_time_str = user_data
            
            if last_scan_time_str:
                
                last_scan_time = datetime.fromisoformat(last_scan_time_str)
            else:
                last_scan_time = None

            # Получение текущего времени
            current_time = datetime.now()

            if last_scan_time is None or (current_time - last_scan_time) >= timedelta(days=1):
                # Обновляем время сканирования
                last_scan_time = current_time
                c.execute("UPDATE users SET last_scan_time=?, free_draws=? WHERE id=?", 
                          (last_scan_time.isoformat(), free_draws + 1, user.id))
                conn.commit()
                print("Время сканирования обновлено успешно.")
                await message.answer("Время бесплатной отрисовки")
            else:
                print("Время сканирования уже обновлено за последние 24 часа.")

        # Если пользователь уже есть в базе данных, пропускаем капчу
        await send_options_menu(message)
    else:
        # Если пользователя нет в базе данных, добавляем его
        await add_user_to_db(user)

        if last_scan_time is None or (current_time - last_scan_time) >= timedelta(days=1):
            # Обновляем время сканирования
            last_scan_time = current_time
            c.execute("UPDATE users SET last_scan_time=?, free_draws=? WHERE id=?", 
                      (last_scan_time.isoformat(), free_draws + 1, user.id))
            conn.commit()
            print("Время сканирования обновлено успешно.")
            await message.answer("Время бесплатной отрисовки")
        else:
            print("Время сканирования уже обновлено за последние 24 часа.")
        
        
        # Проверяем количество доступных бесплатных отрисовок у пользователя
        c.execute("SELECT free_draws FROM users WHERE id=?", (user.id,))
        free_draws = c.fetchone()[0]

        # Генерация капчи
        captcha_text = generate_random_text()
        print(f'Текст капчи: {captcha_text}')
        image = ImageCaptcha(width=280, height=90)
        captcha_image = image.generate_image(captcha_text)
        captcha_image_file = "captcha_image.png"
        captcha_image.save(captcha_image_file)

        # Отправляем изображение капчи пользователю
        with open(captcha_image_file, "rb") as photo:
            await bot.send_photo(message.chat.id, photo, caption='Проверка на бота:')
        
        # Сохраняем текст капчи для данного пользователя
        user_captcha[message.chat.id] = captcha_text
        
# Обработчик текстовых сообщений
@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_message(message: types.Message):
    if message.chat.id in user_captcha:
        captcha_text = user_captcha[message.chat.id]
        if await check_captcha(message.text, captcha_text):
            await asyncio.sleep(2)
            await bot.send_message(message.chat.id, "✅")
            await send_options_menu(message)
            # Удаляем запись о капче после успешной проверки
            del user_captcha[message.chat.id]
        else:
            await message.answer('Неправильный текст капчи.')
            return
    else:
        # Сначала проверяем, не является ли это начальной командой
        if message.text.startswith('/start'):
            await start(message)
            return
        
        # Проверяем, есть ли данные для пользователя и правильный ли формат
        text = [line.strip() for line in message.text.split("\n")]
        if len(text) != 4:
            print('11гв')
            return
        
        await bot.send_message(message.chat.id, 'Отправьте изображение QR-кода.🖥')

        # Сохраняем данные пользователя
        user_data[message.chat.id] = {
            'time': text[0],
            'coin': text[1],
            'pricetime': text[2],
            'x': text[3]
        }

@dp.callback_query_handler() 
async def process_callback_query(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    payment_url = None
    
    if await check_subscription(chat_id):
        print(2)
    else:
        await bot.send_message(chat_id, 'Пожалуйста, подпишитесь на наш канал, чтобы продолжить.🙏', reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton('Подписаться на канал', url=f'https://t.me/{CHANNEL_USERNAME[1:]}'),
            InlineKeyboardButton('Проверить подписку', callback_data='check_subscription')
        ))
    
    if call.data == 'Try':
        c.execute("SELECT free_draws FROM users WHERE id=?", (chat_id,))
        free_draws = c.fetchone()[0]
        
        c.execute("SELECT last_scan_time FROM users WHERE id=?", (chat_id,))
        last_scan_time_str = c.fetchone()[0]
        
        if last_scan_time_str:
            last_scan_time = datetime.fromisoformat(last_scan_time_str)
        else:
            last_scan_time = None
        rounded_last_scan_time = last_scan_time.strftime('%H:%M:%S')
        conn.commit()
                
        if free_draws <=0:
            keyboard = InlineKeyboardMarkup()
            buy = InlineKeyboardButton(text="Пополнить баланс💰", callback_data='balance')
            back = InlineKeyboardButton(text="Назад", callback_data='back')
            keyboard.add(buy)
            keyboard.add(back)
            await bot.send_message(chat_id, f'''       
Исчерпан дневной лимит, приходите завтра в {rounded_last_scan_time}
или
Пополните баланс на 0.1$ через CryptoBot''', reply_markup=keyboard)
            return
        else:
                with open('Image source/TON/ya_example.png', 'rb') as photo_file:
                    await bot.send_photo(
                        chat_id, 
                        photo_file, 
                        caption=f'''
                        Отправь данные в формате:
<code>20:18</code>
<code>Toncoin</code>
<code>Ваше описание</code><i>(Макс. 160 символов)</i>  
<code>Ваша ссылка</code>  
                    ''', 
                    parse_mode='HTML'  # Directly use Telegram's parse_mode
                )
        
    
    elif call.data == 'balance':
        keyboard = InlineKeyboardMarkup(row_width=5) 
        buttons = [InlineKeyboardButton(text=str(i), callback_data=f'balance_{i}') for i in range(1, 11)]
        keyboard.add(*buttons) 
        keyboard.add(InlineKeyboardButton(text='Назад', callback_data='back'))  # Add the "Назад" button at the end
        await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='Введи кол-во отрисовок:', reply_markup=keyboard)
    elif call.data.startswith('balance_'):
        num_draws = int(call.data.split('_')[1])
        amount = 0.1 * num_draws

        c.execute("SELECT free_draws FROM users WHERE id=?", (chat_id,))
        free_draws = c.fetchone()[0]

        payment_url, invoice_id = await create_invoice(amount)
        await main2()
        await bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
        if payment_url:
            markup = InlineKeyboardMarkup(row_width=5)

            await bot.send_message(chat_id, f'Отрисовок сейчас: {free_draws}\nСсылка: {payment_url}')
            if invoice_id:
                payment_status = await check_invoice_payment(invoice_id)
                if payment_status:
                    emoji_message = await bot.send_message(chat_id, "💰")

                    c.execute("UPDATE users SET free_draws = ? WHERE id = ?", (free_draws + num_draws, chat_id))
                    conn.commit()
                    
                    await asyncio.sleep(5)
                    await bot.delete_message(chat_id=emoji_message.chat.id, message_id=emoji_message.message_id)
                    await bot.send_message(chat_id, "Чек успешно оплачен.✅")
                    


                    user_info = await bot.get_chat(chat_id)
                    username = user_info.username

                    await post_to_channel(f"Пользователь {username} ({chat_id}) успешно произвел оплату.", username, chat_id, amount)
                    
                    button = InlineKeyboardButton(text="TON", callback_data='TON')
                    button1 = InlineKeyboardButton(text="💵Пополнить баланс", callback_data='balance')
                    markup.row(button)
                    markup.row(button1)
                    await bot.send_message(chat_id, "Нажми, чтобы отрисовать", reply_markup=markup)
                else:
                    await bot.send_message(chat_id, "Чек не оплачен.❌")
            else:
                await bot.send_message(chat_id, "Не удалось получить ID чека.❌")

                
                
    elif call.data == 'check_subscription':
        if await check_subscription(chat_id):
            markup = InlineKeyboardMarkup()
            button = InlineKeyboardButton(text="TON", callback_data='TON')
            button1 = InlineKeyboardButton(text="💵Пополнить баланс", callback_data='balance')
            markup.row(button)
            markup.row(button1)
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='Подписка подтверждена! Вы можете продолжить.', reply_markup=markup)
        else:
            await bot.send_message(chat_id, 'Вы все еще не подписаны на наш канал.', reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton('Подписаться на канал', url=f'https://t.me/{CHANNEL_USERNAME[1:]}'),
                InlineKeyboardButton('Проверить подписку', callback_data='check_subscription')
            ))
    

    elif call.data == 'TON':
        c.execute("SELECT free_draws FROM users WHERE id=?", (chat_id,))
        free_draws = c.fetchone()[0]
        
        c.execute("SELECT last_scan_time FROM users WHERE id=?", (chat_id,))
        last_scan_time_str = c.fetchone()[0]
        conn.commit()
       

        if free_draws <=0:
            keyboard = InlineKeyboardMarkup()
            buy = InlineKeyboardButton(text="Пополнить баланс", callback_data='balance')
            back = InlineKeyboardButton(text="Назад", callback_data='back')
            keyboard.add(buy)
            keyboard.add(back)
            await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
text=f'''
Исчерпан дневной лимит, приходите завтра в {last_scan_time_str}
или
Пополните баланс на 0.1$ через CryptoBot''', reply_markup=keyboard)
    
            return
        else:
            with open('Image source/TON/ya_example.png', 'rb') as photo_file:
                await bot.send_photo(
                    chat_id, 
                    photo_file, 
                    caption=f'''
                    Отправь данные в формате:
<code>20:18</code>
<code>Toncoin</code>
<code>Ваше описание</code><i>(Макс. 160 символов)</i> 
<code>Ваша ссылка</code>     
                    ''', 
                    parse_mode='HTML'  # Directly use Telegram's parse_mode
                )

    elif call.data == 'back':
        if await check_subscription(chat_id):
                c.execute("SELECT free_draws FROM users WHERE id=?", (chat_id,))
                free_draws = c.fetchone()[0]
                markup = InlineKeyboardMarkup()
                button = InlineKeyboardButton(text="TON", callback_data='TON')
                button1 = InlineKeyboardButton(text="💵Пополнить баланс", callback_data='balance')
                markup.row(button)
                markup.row(button1)
                await bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f'''
Количество отрисовок: {free_draws}

Выбери опцию ниже:''', reply_markup=markup)
                
        else:
            # Если подписка отсутствует, отправляем сообщение с предложением подписаться
            await chat_id.answer('Пожалуйста, подпишитесь на наш канал, чтобы продолжить.', reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton('Подписаться на канал', url=f'https://t.me/{CHANNEL_USERNAME[1:]}'),
                InlineKeyboardButton('Проверить подписку', callback_data='check_subscription')
            ))
        
    
    
    
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def process_qr(message: types.Message):
    global client_session, last_scan_time  # Объявить last_scan_time как глобальную переменную
    try:
        current_time = datetime.now()

        # Получить free_draws
        c.execute("SELECT free_draws FROM users WHERE id=?", (message.chat.id,))
        result = c.fetchone()
        if result:
            free_draws = result[0]
        else:
            await bot.send_message(message.chat.id, 'Ошибка: Не удалось получить информацию о количестве бесплатных попыток.')
            return

        if free_draws <= 0:
            c.execute("SELECT last_scan_time FROM users WHERE id=?", (message.chat.id,))
            last_scan_time_str = c.fetchone()[0]
            conn.commit()
            
            keyboard = InlineKeyboardMarkup()
            buy = InlineKeyboardButton(text="Пополнить баланс", callback_data='balance')
            back = InlineKeyboardButton(text="Назад", callback_data='back')
            keyboard.add(buy)
            keyboard.add(back)
            
            c.execute("SELECT free_draws FROM users WHERE id=?", (message.chat.id,))
            free_draws = c.fetchone()[0]
            conn.commit()
            
            await bot.send_message(message.chat.id, f'''
Исчерпан дневной лимит, приходите завтра в {last_scan_time_str}
или
Пополните баланс на 0.1$ через CryptoBot''', reply_markup=keyboard)
            return
        
        if message.chat.id not in user_data:
            await bot.send_message(message.chat.id, 'Сначала отправьте данные в текстовом формате.')
            return

        file_info = await bot.get_file(message.photo[-1].file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        # Сохранить QR-код
        qr_path = 'Image source/TON/qr_image.png'
        with open(qr_path, 'wb') as new_file:
            new_file.write(downloaded_file.read())

        # Получить данные пользователя
        data = user_data[message.chat.id]
        time = data['time']
        coin = data['coin']
        pricetime = data['pricetime']
        x = data['x']
        
        # Проверить и заменить аббревиатуру монеты
        coin_short = abbreviations.get(coin, coin)

        # Загрузить фон и QR-код
        tink = Image.open("Image source/TON/ya_balance.png").convert("RGBA")
        qr = Image.open(qr_path).convert("RGBA")
        qr = qr.resize((360, 350))  # При необходимости изменить размер QR-кода

        # Загрузить и изменить размер иконки
        icon = Image.open("Image source/TON/icon.png").convert("RGBA")
        icon_size = (80, 80)  # Размер иконки
        icon = icon.resize(icon_size)

        # Наложить иконку на QR-код
        qr.paste(icon, ((qr.width - icon.width) // 2, (qr.height - icon.height) // 2), icon)

        # Загрузить шрифты
        font_time = ImageFont.truetype("Fonts/SF-Pro-Display-Bold.otf", 24)
        font_coin = ImageFont.truetype("Fonts/Inter-Bold.ttf", 32)
        font_pricetime = ImageFont.truetype("Fonts/Inter-Regular.ttf", 24)
        font_x = ImageFont.truetype("Fonts/Inter-Medium.ttf", 25)
        d = ImageDraw.Draw(tink)

        # Обработка текста
        alpha = 130  # Прозрачность текста (0-255)

        
        pricetime_lines = pricetime.split()
        max_chars_per_line = 20  # Максимальное количество символов на строке
        lines = []
        current_line = []
        for word in pricetime_lines:
            if len(" ".join(current_line + [word])) <= max_chars_per_line:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        # Создать прозрачное изображение для текста
        text_image = Image.new("RGBA", tink.size, (255, 255, 255, 0))
        d_text = ImageDraw.Draw(text_image)

        # Разделить и центрировать каждую строку из lines
        y_text_position = 275
        for line in lines:
            line_width, _ = d_text.textsize(line, font=font_pricetime)
            line_x_position = (tink.width - line_width) // 2
            d_text.text((line_x_position, y_text_position), line, font=font_pricetime, fill=(255, 255, 255, alpha))
            y_text_position += font_pricetime.getsize(line)[1] + 3
        
        
        
        # Рассчитать ширину текста "X"
        text_width, _ = d.textsize(x, font=font_x)

        # Рассчитать x-координату для центрирования текста
        x_text_x_position = (tink.width - text_width) // 2

        # Нарисовать текст "X" с новой x-координатой
        d.text((x_text_x_position, 910), x, font=font_x, fill=(0, 0, 0, 255))

        # Нарисовать непрозрачные тексты на основном изображении
        text_width_coin, _ = d.textsize(coin, font=font_coin)
        x_coin_position = (tink.width - text_width_coin) // 2
        d.text((46, 21), time, font=font_time, fill=(255, 255, 255, 255))
        d.text((x_coin_position, 233), coin, font=font_coin, fill=(255, 255, 255, 255))

        # Совместить прозрачный текст с основным изображением
        combined = Image.alpha_composite(tink, text_image)

        # Рассчитать координаты для центрирования QR-кода
        center_x = (combined.width - qr.width) // 2

        # Добавить QR-код на изображение
        combined.paste(qr, (center_x, 500), qr)
        
        combined.save('Image source/TON/ton.png')
        combined.save('Image source/TON/ton.pdf')
        photo_file = types.InputFile("Image source/TON/ton.png")
        
        pdf_path = "Image source/TON/ton.pdf"
        pdf_file = types.InputFile(pdf_path)
        
        markup = InlineKeyboardMarkup()
        button = InlineKeyboardButton(text="Сделать снова", callback_data='Try')
        markup.row(button)

        # Обновить free_draws в базе данных
        c.execute("UPDATE users SET free_draws = ? WHERE id = ?", (free_draws - 1, message.chat.id))
        conn.commit()
        
        await bot.send_document(message.chat.id, pdf_file)
        await bot.send_photo(message.chat.id, photo_file, reply_markup=markup)
        

        os.remove('Image source/TON/ton.pdf')
        os.remove('Image source/TON/ton.png')
         
    except Exception as e:
        await bot.send_message(message.chat.id, f'Произошла ошибка: {e}')
    
