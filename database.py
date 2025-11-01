import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        # Pega a string de conexão do Neon do arquivo .env
        database_url = os.getenv('DATABASE_URL')
        
        # Conecta ao PostgreSQL
        connection = psycopg2.connect(database_url)
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None