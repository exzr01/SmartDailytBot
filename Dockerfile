# Вказуємо легкий образ Python
FROM python:3.10-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо dependencies
COPY requirements.txt .

# Встановлюємо pip-залежності
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копіюємо весь код
COPY . .

# Вказуємо команду запуску
CMD ["python", "main.py"]
