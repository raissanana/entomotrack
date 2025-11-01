import os
import asyncio
from sqlalchemy import text
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

async def explore_database():
    original_url = os.getenv('DATABASE_URL')
    clean_url = original_url.split('?')[0]
    async_url = clean_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(async_url, echo=False, connect_args={"ssl": "require"})
    
    try:
        async with engine.connect() as conn:
            print("🔍 EXPLORANDO O BANCO DE DADOS")
            print("=" * 50)
            
            # 1. Informações do banco
            print("\n📊 INFORMAÇÕES DO BANCO:")
            result = await conn.execute(text("""
                SELECT 
                    version() as postgres_version,
                    current_database() as db_name,
                    current_user as username,
                    current_schema() as schema
            """))
            info = result.fetchone()
            print(f"   PostgreSQL: {info[0]}")
            print(f"   Database: {info[1]}")
            print(f"   Usuário: {info[2]}")
            print(f"   Schema: {info[3]}")
            
            print("\n📋 TABELAS EXISTENTES:")
            result = await conn.execute(text("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            if tables:
                for table in tables:
                    print(f"   📁 {table[0]} ({table[1]})")
                    
                    # Mostrar colunas de cada tabela
                    result = await conn.execute(text(f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name = '{table[0]}'
                        ORDER BY ordinal_position
                    """))
                    columns = result.fetchall()
                    for col in columns:
                        print(f"      └─ {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
            else:
                print("   ℹ️  Nenhuma tabela encontrada no schema public")
            
            # 3. Contar registros (se houver tabelas)
            if tables:
                print("\n📊 CONTAGEM DE REGISTROS:")
                for table in tables:
                    if table[1] == 'BASE TABLE':  # Apenas tabelas, não views
                        result = await conn.execute(text(f"SELECT COUNT(*) FROM {table[0]}"))
                        count = result.scalar()
                        print(f"   {table[0]}: {count} registros")
            
            print("\n🎉 EXPLORAÇÃO CONCLUÍDA!")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        await engine.dispose()

asyncio.run(explore_database())