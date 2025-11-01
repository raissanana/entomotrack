import os
import asyncio
import re
from sqlalchemy import text
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

async def async_main() -> None:
    # Pega a string de conexão
    database_url = os.getenv('DATABASE_URL')
    
    # Remove os parâmetros de query problemáticos para asyncpg
    database_url = database_url.replace('?sslmode=require', '')
    
    # Converte para formato asyncpg
    async_database_url = re.sub(r'^postgresql:', 'postgresql+asyncpg:', database_url)
    
    print(f"Conectando com: {async_database_url}")
    
    # Configurações SSL para asyncpg
    connect_args = {
        "ssl": "require"  # Asyncpg usa "ssl" em vez de "sslmode"
    }
    
    engine = create_async_engine(async_database_url, echo=True, connect_args=connect_args)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("select 'hello world'"))
            print(result.fetchall())
            print("✅ Conexão bem-sucedida!")
    except Exception as e:
        print(f"Erro na conexão: {e}")
    finally:
        await engine.dispose()

asyncio.run(async_main())