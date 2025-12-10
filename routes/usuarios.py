from flask import Blueprint, request, jsonify
from database import get_connection
from psycopg2.extras import RealDictCursor

usuarios_bp = Blueprint("usuarios", __name__)

@usuarios_bp.route("", methods=["GET", "OPTIONS"])
def listar_usuarios():
    if request.method == "OPTIONS":
        return ("", 200)

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM usuario;")
            usuarios = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "data": usuarios}), 200
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao listar usuários: {str(e)}"}), 500

@usuarios_bp.route("/<int:id_usuario>", methods=["GET"])
def obter_usuario(id_usuario):
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM usuario WHERE idusuario = %s;", (id_usuario,))
            usuario = cursor.fetchone()
        conn.close()
        if usuario:
            return jsonify({"success": True, "data": usuario}), 200
        return jsonify({"success": False, "erro": "Usuário não encontrado"}), 404
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao obter usuário: {str(e)}"}), 500

@usuarios_bp.route("", methods=["POST", "OPTIONS"])
def criar_usuario():
    if request.method == "OPTIONS":
        return ("", 200)

    dados = request.get_json() or {}
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    # Validação básica - campos obrigatórios
    required = ["nome", "email", "senha", "funcao"]
    erros_campo = {}
    for campo in required:
        if not dados.get(campo) or str(dados.get(campo)).strip() == "":
            erros_campo[campo] = "Campo obrigatório"
    if erros_campo:
        conn.close()
        return jsonify({"success": False, "errors": erros_campo}), 400

    try:
        with conn.cursor() as cursor:
            # Verifica email duplicado
            cursor.execute("SELECT 1 FROM usuario WHERE email = %s;", (dados['email'],))
            if cursor.fetchone():
                conn.close()
                return jsonify({"success": False, "errors": {"email": "Este e-mail já está cadastrado"}}), 400

            # Cria usuário
            cursor.execute("""
                INSERT INTO usuario (nome, email, senha, funcao, telefone)
                VALUES (%s, %s, %s, %s, %s) RETURNING idusuario;
            """, (dados['nome'], dados['email'], dados['senha'], dados['funcao'], dados.get('telefone', '')))
            novo_id_usuario = cursor.fetchone()[0]

            id_agente = None
            id_supervisor = None

            # Se for agente, exige matrícula (verifica duplicidade)
            if dados['funcao'] == 'agente':
                if 'matricula' not in dados or not str(dados.get('matricula')).strip():
                    conn.rollback()
                    conn.close()
                    return jsonify({"success": False, "errors": {"matricula": "Matrícula é obrigatória para agentes"}}), 400

                # checar duplicidade de matrícula na tabela agente
                cursor.execute("SELECT 1 FROM agente WHERE matricula = %s;", (dados['matricula'],))
                if cursor.fetchone():
                    conn.rollback()
                    conn.close()
                    return jsonify({"success": False, "errors": {"matricula": "Esta matrícula já está cadastrada"}}), 400

                quartelaria = dados.get('quartelaria', 100)
                cursor.execute("""
                    INSERT INTO agente (quartelaria, matricula, idusuario)
                    VALUES (%s, %s, %s) RETURNING idagente;
                """, (quartelaria, dados['matricula'], novo_id_usuario))
                id_agente = cursor.fetchone()[0]

            elif dados['funcao'] == 'supervisor':
                if 'matricula' not in dados or not str(dados.get('matricula')).strip():
                    conn.rollback()
                    conn.close()
                    return jsonify({"success": False, "errors": {"matricula": "Matrícula é obrigatória para supervisores"}}), 400

                cursor.execute("SELECT 1 FROM supervisor WHERE matricula = %s;", (dados['matricula'],))
                if cursor.fetchone():
                    conn.rollback()
                    conn.close()
                    return jsonify({"success": False, "errors": {"matricula": "Esta matrícula já está cadastrada"}}), 400

                cursor.execute("""
                    INSERT INTO supervisor (matricula, idusuario)
                    VALUES (%s, %s) RETURNING idsupervisor;
                """, (dados['matricula'], novo_id_usuario))
                id_supervisor = cursor.fetchone()[0]

            conn.commit()

        resposta = {
            "success": True,
            "mensagem": "Usuário criado com sucesso",
            "id_usuario": novo_id_usuario
        }
        if id_agente:
            resposta["id_agente"] = id_agente
            resposta["matricula"] = dados.get('matricula')
        if id_supervisor:
            resposta["id_supervisor"] = id_supervisor
            resposta["matricula"] = dados.get('matricula')

        return jsonify(resposta), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao criar usuário: {str(e)}"}), 500

@usuarios_bp.route("/<int:id_usuario>", methods=["PUT"])
def atualizar_usuario(id_usuario):
    dados = request.get_json() or {}
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE usuario
                SET nome=%s, email=%s, senha=%s, funcao=%s, telefone=%s
                WHERE idusuario=%s;
            """, (dados.get('nome'), dados.get('email'), dados.get('senha'),
                  dados.get('funcao'), dados.get('telefone', ''), id_usuario))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "mensagem": "Usuário atualizado com sucesso"}), 200
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao atualizar usuário: {str(e)}"}), 500

@usuarios_bp.route("/<int:id_usuario>", methods=["DELETE"])
def deletar_usuario(id_usuario):
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM usuario WHERE idusuario=%s;", (id_usuario,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "mensagem": "Usuário deletado com sucesso"}), 200
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao deletar usuário: {str(e)}"}), 500