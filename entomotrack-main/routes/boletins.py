from flask import Blueprint, request, jsonify
from database import get_connection

boletins_bp = Blueprint('boletins', __name__)

@boletins_bp.route('/', methods=['GET'])
def listar_boletins():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.id_boletim, b.data, b.total_casos, b.observacoes,
               ag.matricula AS agente_matricula, bai.nome AS bairro
        FROM boletim_diario b
        JOIN agente_endemias ag ON b.id_agente = ag.id_agente
        JOIN bairro bai ON b.id_bairro = bai.id_bairro;
    """)
    boletins = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(boletins)

@boletins_bp.route('/<int:id_boletim>', methods=['GET'])
def obter_boletim(id_boletim):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.id_boletim, b.data, b.total_casos, b.observacoes,
               ag.matricula AS agente_matricula, bai.nome AS bairro
        FROM boletim_diario b
        JOIN agente_endemias ag ON b.id_agente = ag.id_agente
        JOIN bairro bai ON b.id_bairro = bai.id_bairro
        WHERE b.id_boletim = %s;
    """, (id_boletim,))
    boletim = cursor.fetchone()
    cursor.close()
    connection.close()
    if boletim:
        return jsonify(boletim)
    return jsonify({"erro": "Boletim não encontrado"}), 404

@boletins_bp.route('/', methods=['POST'])
def criar_boletim():
    dados = request.get_json()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO boletim_diario (id_agente, id_bairro, data, total_casos, observacoes)
        VALUES (%s, %s, %s, %s, %s);
    """, (dados['id_agente'], dados['id_bairro'], dados['data'], dados['total_casos'], dados['observacoes']))
    connection.commit()
    novo_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Boletim criado com sucesso", "id_boletim": novo_id}), 201

@boletins_bp.route('/<int:id_boletim>', methods=['PUT'])
def atualizar_boletim(id_boletim):
    dados = request.get_json()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE boletim_diario
        SET id_agente=%s, id_bairro=%s, data=%s, total_casos=%s, observacoes=%s
        WHERE id_boletim=%s;
    """, (dados['id_agente'], dados['id_bairro'], dados['data'], dados['total_casos'], dados['observacoes'], id_boletim))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Boletim atualizado com sucesso"})

@boletins_bp.route('/<int:id_boletim>', methods=['DELETE'])
def deletar_boletim(id_boletim):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM boletim_diario WHERE id_boletim=%s;", (id_boletim,))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({"mensagem": "Boletim deletado com sucesso"})
