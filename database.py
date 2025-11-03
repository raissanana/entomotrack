import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    Retorna uma conexão psycopg2 ou None em caso de falha.
    Use com cuidado: sempre feche a conexão após uso.
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL não definido no .env")
        connection = psycopg2.connect(database_url)
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None