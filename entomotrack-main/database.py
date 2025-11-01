import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='entomotrack',     # nome do banco conforme seu modelo
            user='root',                # altere se necessário
            password='123456'           # altere se necessário
        )
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None
