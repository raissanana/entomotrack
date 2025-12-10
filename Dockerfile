FROM python:3.10-slim

WORKDIR /app

# Copiar requirements primeiro (cache otimizado)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Comando de migração (se precisar de banco de dados)
# RUN flask db upgrade  # Descomente se usar Flask-Migrate

# Comando principal
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120