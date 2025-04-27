# Telegram Bot для передачи показаний счетчиков

Бот предназначен для сбора показаний счетчиков воды, электричества и тепла от жильцов многоквартирного дома.

## Основной функционал

- Регистрация пользователей (номер квартиры, ФИО)
- Подача показаний счетчиков
- Проверка на корректность показаний (не меньше предыдущих)
- История подачи показаний

## Функционал администратора

- Добавление/удаление пользователей
- Просмотр/редактирование данных пользователей
- Рассылка уведомлений
- Экспорт данных в Excel

## Доступные команды

- `/start` - регистрация/просмотр профиля
- `/submit` - подать показания счетчиков
- `/edit_serials` - редактировать серийные номера счётчиков

**Команды администратора:**

- `/admin` - вход в админ-панель (доступно только для администраторов)

## Структура базы данных

Бот использует SQLite базу данных со следующими таблицами:

1. `users` - информация о пользователях
   - user_id (Telegram ID)
   - apartment_number (номер квартиры)
   - first_name, last_name

2. `meter_types` - типы счетчиков
   - type_id
   - name (electricity, heat, hot_water, cold_water)
   - unit (единицы измерения)

3. `meters` - счетчики
   - meter_id
   - apartment_number
   - type_id
   - count_meter

4. `serials` - серийные номера счетчиков
   - serial_id
   - meter_id
   - serial_number

5. `readings` - показания счетчиков
   - reading_id
   - meter_id
   - user_id (кто подал)
   - value (значение)
   - reading_date (дата подачи)

6. `meter_descriptions` - описания счетчиков
   - desc_id
   - serial_id
   - description

## Запуск с помощью Docker Compose

1.  Установите Docker и Docker Compose.

2.  Клонируйте репозиторий:
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

3.  Создайте файл `.env` на основе примера:
    ```
    DB_LITE=sqlite+aiosqlite:///YOUR_DB.db
    BOT_TOKEN=YOUR_BOT_TOKEN
    ADMIN_IDS=[]
    MODE=DEV
    ```
    Замените `YOUR_BOT_TOKEN` на токен вашего бота, а `ADMIN_IDS` на список Telegram ID администраторов.

4.  Запустите приложение с помощью Docker Compose:
    ```bash
    docker-compose up -d
    ```

## Конфигурация

Основные настройки хранятся в файле `.env` и передаются через переменные окружения:

- `DB_LITE` - URL базы данных SQLite
- `BOT_TOKEN` - токен Telegram бота
- `ADMIN_IDS` - список Telegram ID администраторов
- `MODE` - режим работы (DEV или PROD)

Логирование:

- Логи сохраняются в файл `logs.log`
- Уровень логирования: INFO для консоли, ERROR для файла

## Технологии

- Python 3.12+
- Aiogram 3.x
- SQLAlchemy 2.x
- SQLite
- Docker
- Docker Compose
