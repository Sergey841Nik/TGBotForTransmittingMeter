FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Включить компиляцию байт-кода
ENV UV_COMPILE_BYTECODE=1

# Копируем из кэша вместо привязки, поскольку это подключенный том
ENV UV_LINK_MODE=copy

# Устанавливаем необходимые локали
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=ru_RU.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем переменные окружения для локали
ENV LANG=ru_RU.UTF-8 \
    LC_ALL=ru_RU.UTF-8

# Устанавливаем зависимости проекта, используя файл блокировки и настройки
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Затем добавляем остальной исходный код проекта и установите его
# Установка отдельно от зависимостей обеспечивает оптимальное кэширование слоев
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Сбрасываем точку входа, чтобы не вызывайте `uv`
ENTRYPOINT []


CMD ["python3.12", "main.py"]

