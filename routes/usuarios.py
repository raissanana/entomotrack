from flask import Blueprint, request, jsonify
from database import get_connection
from psycopg2.extras import RealDictCursor

# 1. PRIMEIRO define o Blueprint
usuarios_bp = Blueprint('usuarios', __name__)

# 2. DEPOIS define as rotas
@usuarios_bp.route('/', methods=['GET'])
def listar_usuarios():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM usuario;")
    usuarios = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(usuarios)

@usuarios_bp.route('/<int:id_usuario>', methods=['GET'])
def obter_usuario(id_usuario):
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM usuario WHERE idusuario = %s;", (id_usuario,))
    usuario = cursor.fetchone()
    cursor.close()
    connection.close()
    if usuario:
        return jsonify(usuario)
    return jsonify({"erro": "Usuário não encontrado"}), 404

@usuarios_bp.route('/', methods=['POST'])
def criar_usuario():
    dados = request.get_json()
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        # 1. Cria o usuário
        cursor.execute("""
            INSERT INTO usuario (nome, email, senha, funcao, telefone)
            VALUES (%s, %s, %s, %s, %s) RETURNING idusuario;
        """, (dados['nome'], dados['email'], dados['senha'], dados['funcao'], dados['telefone']))
        
        novo_id_usuario = cursor.fetchone()[0]
        
        # 2. Se for agente, cria automaticamente na tabela agente
        if dados['funcao'] == 'agente':
            # Verifica se a matrícula foi fornecida
            if 'matricula' not in dados:
                connection.rollback()
                cursor.close()
                connection.close()
                return jsonify({"erro": "Matrícula é obrigatória para agentes"}), 400
                
            quartelaria = dados.get('quartelaria', 100)  # Padrão 100 se não informado
            
            cursor.execute("""
                INSERT INTO agente (quartelaria, matricula, idusuario) 
                VALUES (%s, %s, %s) RETURNING idagente;
            """, (quartelaria, dados['matricula'], novo_id_usuario))
            id_agente = cursor.fetchone()[0]
            
        # 3. Se for supervisor, cria automaticamente na tabela supervisor
        elif dados['funcao'] == 'supervisor':
            # Verifica se a matrícula foi fornecida
            if 'matricula' not in dados:
                connection.rollback()
                cursor.close()
                connection.close()
                return jsonify({"erro": "Matrícula é obrigatória para supervisores"}), 400
                
            cursor.execute("""
                INSERT INTO supervisor (matricula, idusuario) 
                VALUES (%s, %s) RETURNING idsupervisor;
            """, (dados['matricula'], novo_id_usuario))
            id_supervisor = cursor.fetchone()[0]
            
        connection.commit()
        
        resposta = {
            "mensagem": "Usuário criado com sucesso", 
            "id_usuario": novo_id_usuario
        }
        
        # Adiciona info extra se for agente ou supervisor
        if dados['funcao'] == 'agente':
            resposta["id_agente"] = id_agente
            resposta["matricula"] = dados['matricula']
        elif dados['funcao'] == 'supervisor':
            resposta["id_supervisor"] = id_supervisor
            resposta["matricula"] = dados['matricula']
            
        cursor.close()
        connection.close()
        return jsonify(resposta), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao criar usuário: {str(e)}"}), 500

@usuarios_bp.route('/<int:id_usuario>', methods=['PUT'])
def atualizar_usuario(id_usuario):
    dados = request.get_json()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE usuario
        SET nome=%s, email=%s, senha=%s, funcao=%s, telefone=%s
        WHERE idusuario=%s;
    """, (dados['nome'], dados['email'], dados['senha'], dados['funcao'], dados['telefone'], id_usuario))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Usuário atualizado com sucesso"})

@usuarios_bp.route('/<int:id_usuario>', methods=['DELETE'])
def deletar_usuario(id_usuario):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM usuario WHERE idusuario=%s;", (id_usuario,))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Usuário deletado com sucesso"})