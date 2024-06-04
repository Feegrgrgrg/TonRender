from aiogram import Bot, Dispatcher, executor
from config import TOKEN
from bot.handlers import start1, admin_command, start
from bot.handlers import dp



async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(bot)
    dp.register_message_handler(start1, commands=['start'])  # Регистрация обработчика
    dp.register_message_handler(admin_command, commands=['admin']) 
    dp.register_message_handler(start, commands=['draws']) 
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    
async def on_startup(_):
    print("Бот онлайн!")
    


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
    