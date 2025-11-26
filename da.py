import aiosqlite
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.client.default import DefaultBotProperties

# Состояния для анкеты
class ProfileStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_city = State()
    waiting_bio = State()
    waiting_photo = State()

# Токен бота
BOT_TOKEN = "8590470502:AAE-MkOEeRhB7xNn8b96mBdpCs9kJ4rWDE4"

# ID администратора (замените на ваш Telegram ID)
ADMIN_ID = 7788088499  # Замените на ваш реальный ID

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# Глобальное соединение с БД
db = None

# Основное меню кнопок
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Создать анкету"), KeyboardButton(text="👤 Моя анкета")],
        [KeyboardButton(text="🔍 Найти анкеты"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)

# Меню отмены
cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

# Инициализация базы данных
async def init_db():
    global db
    db = await aiosqlite.connect('flood.db')
    
    # Настройки для лучшей производительности
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute("PRAGMA synchronous=NORMAL")
    
    # Создаем таблицу
    await db.execute("""
        CREATE TABLE IF NOT EXISTS flood (
            users_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT NOT NULL,
            bio TEXT NOT NULL,
            photo TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()
    print("✅ База данных инициализирована")

# Функция для сохранения профиля
async def save_profile(user_id, full_name, username, name, age, city, bio, photo):
    try:
        # Проверяем, есть ли уже запись
        cursor = await db.execute("SELECT users_id FROM flood WHERE users_id = ?", (user_id,))
        existing_user = await cursor.fetchone()
        
        if existing_user:
            # Обновляем существующую запись
            await db.execute("""
                UPDATE flood SET 
                full_name = ?, username = ?, name = ?, age = ?, city = ?, bio = ?, photo = ?
                WHERE users_id = ?
            """, (full_name, username, name, age, city, bio, photo, user_id))
            action = "обновлена"
        else:
            # Вставляем новую запись
            await db.execute("""
                INSERT INTO flood 
                (users_id, full_name, username, name, age, city, bio, photo) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, full_name, username, name, age, city, bio, photo))
            action = "создана"
        
        await db.commit()
        return True, action
        
    except Exception as e:
        print(f"❌ Ошибка сохранения для user_id {user_id}: {e}")
        return False, str(e)

# Проверка является ли пользователь администратором
def is_admin(user_id):
    return user_id == ADMIN_ID

# Команда /start - главное меню
@dp.message(Command("start"))
async def start_command(message: types.Message):
    welcome_text = (
        "👋 Привет! Я бот для создания и поиска анкет.\n\n"
        "📝 <b>Создать анкету</b> - заполните информацию о себе\n"
        "👤 <b>Моя анкета</b> - посмотреть свою анкету\n"
        "🔍 <b>Найти анкеты</b> - посмотреть анкеты других пользователей\n"
        "ℹ️ <b>Помощь</b> - показать это сообщение\n\n"
        "Выберите действие на клавиатуре ниже 👇"
    )
    
    await message.answer(welcome_text, reply_markup=main_menu)

# Команда /help
@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def help_command(message: types.Message):
    help_text = (
        "📋 <b>Доступные команды:</b>\n\n"
        "📝 <b>Создать анкету</b> - заполните информацию о себе\n"
        "👤 <b>Моя анкета</b> - посмотреть свою анкету\n"
        "🔍 <b>Найти анкеты</b> - посмотреть анкеты других пользователей\n\n"
        "Также вы можете использовать команды:\n"
        "/start - главное меню\n"
        "/help - эта справка\n"
        "/debug - отладочная информация (только для админа)"
    )
    await message.answer(help_text, reply_markup=main_menu)

# Команда для отладки (работает везде, но только для админа)
@dp.message(Command("debug"))
async def debug_profiles(message: types.Message):
    # Проверяем права доступа
    if not is_admin(message.from_user.id):
        # В группах не отвечаем не-админам, чтобы не засорять чат
        if message.chat.type == "private":
            await message.answer("❌ У вас нет прав доступа к этой команде.")
        return
    
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM flood")
        count = await cursor.fetchone()
        
        cursor = await db.execute("SELECT users_id, name, age, city FROM flood")
        profiles = await cursor.fetchall()
        
        result = f"📊 <b>Статистика базы данных:</b>\n\n"
        result += f"📈 Всего анкет: {count[0]}\n\n"
        
        if profiles:
            result += "<b>Список анкет:</b>\n"
            for user_id, name, age, city in profiles:
                result += f"👤 ID: {user_id}, {name}, {age} лет, {city}\n"
        else:
            result += "Анкет нет в базе данных"
            
        await message.answer(result)
        
    except Exception as e:
        await message.answer(f"Ошибка при получении данных: {e}")

# Кнопка "Создать анкету"
@dp.message(F.text == "📝 Создать анкету")
async def start_anketa(message: types.Message, state: FSMContext):
    await message.answer(
        "📝 Давайте создадим вашу анкету!\n\n"
        "Как вас зовут? (Имя и фамилия)",
        reply_markup=cancel_menu
    )
    await state.set_state(ProfileStates.waiting_name)

# Кнопка "Моя анкета"
@dp.message(F.text == "👤 Моя анкета")
async def my_profile_button(message: types.Message):
    await show_profile(message)

# Кнопка "Найти анкеты"
@dp.message(F.text == "🔍 Найти анкеты")
async def search_profiles_button(message: types.Message):
    await search_profiles(message)

# Обработчик отмены
@dp.message(F.text == "❌ Отмена")
async def cancel_anketa(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Заполнение анкеты отменено", reply_markup=main_menu)

# Шаг 1: Имя
@dp.message(ProfileStates.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя должно содержать минимум 2 символа. Попробуйте еще раз:")
        return
    
    await state.update_data(name=name)
    await message.answer("Сколько вам лет?")
    await state.set_state(ProfileStates.waiting_age)

# Шаг 2: Возраст
@dp.message(ProfileStates.waiting_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число:")
        return
    
    age = int(message.text)
    if age < 12 or age > 100:
        await message.answer("Пожалуйста, введите реальный возраст (12-100):")
        return
    
    await state.update_data(age=age)
    await message.answer("Из какого вы города?")
    await state.set_state(ProfileStates.waiting_city)

# Шаг 3: Город
@dp.message(ProfileStates.waiting_city)
async def process_city(message: types.Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Название города должно содержать минимум 2 символа. Попробуйте еще раз:")
        return
    
    await state.update_data(city=city)
    await message.answer("Расскажите о себе (интересы, хобби, увлечения и т.д.):")
    await state.set_state(ProfileStates.waiting_bio)

# Шаг 4: О себе
@dp.message(ProfileStates.waiting_bio)
async def process_bio(message: types.Message, state: FSMContext):
    bio = message.text.strip()
    if len(bio) < 10:
        await message.answer("Расскажите о себе подробнее (минимум 10 символов):")
        return
    if len(bio) > 500:
        await message.answer("Слишком длинный текст. Пожалуйста, сократите до 500 символов:")
        return
    
    await state.update_data(bio=bio)
    await message.answer("📸 Отлично! Теперь отправьте ваше фото:")
    await state.set_state(ProfileStates.waiting_photo)

# Шаг 5: Фото и сохранение в БД
@dp.message(ProfileStates.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    try:
        # Получаем данные из состояния
        user_data = await state.get_data()
        
        # Сохраняем информацию о фото (file_id)
        photo = message.photo[-1]
        photo_file_id = photo.file_id
        
        # Сохраняем в базу данных
        success, action = await save_profile(
            message.from_user.id,
            message.from_user.full_name,
            message.from_user.username,
            user_data['name'],
            user_data['age'],
            user_data['city'],
            user_data['bio'],
            photo_file_id
        )
        
        if success:
            # Показываем результат пользователю
            await message.answer_photo(
                photo=photo_file_id,
                caption=f"✅ Анкета успешно {action}!\n\n"
                       f"👤 <b>Имя:</b> {user_data['name']}\n"
                       f"🎂 <b>Возраст:</b> {user_data['age']}\n"
                       f"🏙️ <b>Город:</b> {user_data['city']}\n"
                       f"📝 <b>О себе:</b> {user_data['bio']}\n\n"
                       f"Чтобы посмотреть свою анкету, нажмите «👤 Моя анкета»",
                reply_markup=main_menu
            )
            
            await state.clear()
        else:
            await message.answer(
                f"❌ Ошибка при сохранении анкеты: {action}\n\nПопробуйте еще раз.",
                reply_markup=main_menu
            )
            await state.clear()
        
    except Exception as e:
        print(f"❌ Общая ошибка при сохранении анкеты: {e}")
        await message.answer(
            f"❌ Произошла непредвиденная ошибка. Попробуйте начать заново.",
            reply_markup=main_menu
        )
        await state.clear()

# Если отправили не фото
@dp.message(ProfileStates.waiting_photo)
async def process_photo_invalid(message: types.Message):
    await message.answer("Пожалуйста, отправьте фото:")

# Команда для просмотра своей анкеты
@dp.message(Command("myprofile"))
async def show_profile(message: types.Message):
    try:
        cursor = await db.execute(
            "SELECT * FROM flood WHERE users_id = ?", 
            (message.from_user.id,)
        )
        profile = await cursor.fetchone()
        
        if profile:
            users_id, full_name, username, name, age, city, bio, photo, created_at = profile
            
            await message.answer_photo(
                photo=photo,
                caption=f"📋 <b>Ваша анкета:</b>\n\n"
                       f"👤 <b>Имя:</b> {name}\n"
                       f"🎂 <b>Возраст:</b> {age}\n"
                       f"🏙️ <b>Город:</b> {city}\n"
                       f"📝 <b>О себе:</b> {bio}\n\n"
                       f"🕐 <b>Создана:</b> {created_at}",
                reply_markup=main_menu
            )
        else:
            await message.answer(
                "У вас еще нет анкеты. Создайте её, нажав «📝 Создать анкету»",
                reply_markup=main_menu
            )
            
    except Exception as e:
        print(f"❌ Ошибка при загрузке анкеты: {e}")
        await message.answer(f"Ошибка при загрузке анкеты: {e}")

# Команда для поиска анкет
@dp.message(Command("search"))
async def search_profiles(message: types.Message):
    try:
        cursor = await db.execute(
            "SELECT name, age, city, bio, photo FROM flood WHERE users_id != ? LIMIT 5",
            (message.from_user.id,)
        )
        profiles = await cursor.fetchall()
        
        if profiles:
            for name, age, city, bio, photo in profiles:
                bio_preview = bio[:100] + "..." if len(bio) > 100 else bio
                caption = f"🔍 <b>Найдена анкета:</b>\n\n" \
                         f"👤 <b>Имя:</b> {name}\n" \
                         f"🎂 <b>Возраст:</b> {age}\n" \
                         f"🏙️ <b>Город:</b> {city}\n" \
                         f"📝 <b>О себе:</b> {bio_preview}"
                
                await message.answer_photo(
                    photo=photo,
                    caption=caption
                )
        else:
            await message.answer(
                "Пока нет других анкет или вы единственный пользователь.",
                reply_markup=main_menu
            )
            
    except Exception as e:
        await message.answer(f"Ошибка при поиске: {e}")

# Обработчик для любых других сообщений
@dp.message()
async def other_messages(message: types.Message):
    # Игнорируем сообщения в группах, если это не команда
    if message.chat.type != "private":
        return
        
    await message.answer(
        "Используйте кнопки меню для навигации:\n\n"
        "📝 <b>Создать анкету</b> - заполнить информацию о себе\n"
        "👤 <b>Моя анкета</b> - посмотреть свою анкету\n"
        "🔍 <b>Найти анкеты</b> - посмотреть анкеты других\n"
        "ℹ️ <b>Помощь</b> - показать справку",
        reply_markup=main_menu
    )

# Запуск бота
async def main():
    # Инициализация базы данных при старте
    await init_db()
    
    try:
        print("🤖 Бот запущен...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
    finally:
        # Закрываем соединение с БД при завершении
        if db:
            await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())