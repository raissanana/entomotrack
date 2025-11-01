from flask import Blueprint, request, jsonify
from database import get_connection

usuarios_bp = Blueprint('usuarios', __name__)

@usuarios_bp.route('/', methods=['GET'])
def listar_usuarios():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario;")
    usuarios = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(usuarios)

@usuarios_bp.route('/<int:id_usuario>', methods=['GET'])
def obter_usuario(id_usuario):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s;", (id_usuario,))
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
    cursor.execute("""
        INSERT INTO usuario (nome, email, senha, funcao, telefone)
        VALUES (%s, %s, %s, %s, %s);
    """, (dados['nome'], dados['email'], dados['senha'], dados['funcao'], dados['telefone']))
    connection.commit()
    novo_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Usuário criado com sucesso", "id_usuario": novo_id}), 201

@usuarios_bp.route('/<int:id_usuario>', methods=['PUT'])
def atualizar_usuario(id_usuario):
    dados = request.get_json()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE usuario
        SET nome=%s, email=%s, senha=%s, funcao=%s, telefone=%s
        WHERE id_usuario=%s;
    """, (dados['nome'], dados['email'], dados['senha'], dados['funcao'], dados['telefone'], id_usuario))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Usuário atualizado com sucesso"})

@usuarios_bp.route('/<int:id_usuario>', methods=['DELETE'])
def deletar_usuario(id_usuario):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM usuario WHERE id_usuario=%s;", (id_usuario,))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Usuário deletado com sucesso"})
