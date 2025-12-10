from flask import Blueprint, request, jsonify
from database import get_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime

formularios_bp = Blueprint('formularios', __name__)

@formularios_bp.route("", methods=["GET", "OPTIONS"])
def listar_formularios():
    if request.method == "OPTIONS":
        return ("", 200)

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT f.*, ag.matricula AS agente_matricula
                FROM formularioporcasa f
                JOIN agente ag ON f.idagente = ag.idagente
                ORDER BY f.data DESC;
            """)
            formularios = cursor.fetchall()

        # normaliza campos de hora para string
        for formulario in formularios:
            if formulario.get('hora_inicio'):
                formulario['hora_inicio'] = str(formulario['hora_inicio'])
            if formulario.get('hora_saida'):
                formulario['hora_saida'] = str(formulario['hora_saida'])

        conn.close()
        return jsonify({"success": True, "data": formularios}), 200
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao listar formulários: {str(e)}"}), 500

@formularios_bp.route("/<int:id_formulario>", methods=["GET"])
def obter_formulario(id_formulario):
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT f.*, ag.matricula AS agente_matricula
                FROM formularioporcasa f
                JOIN agente ag ON f.idagente = ag.idagente
                WHERE f.idboletimdiario = %s;
            """, (id_formulario,))
            formulario = cursor.fetchone()

        conn.close()
        if formulario:
            if formulario.get('hora_inicio'):
                formulario['hora_inicio'] = str(formulario['hora_inicio'])
            if formulario.get('hora_saida'):
                formulario['hora_saida'] = str(formulario['hora_saida'])
            return jsonify({"success": True, "data": formulario}), 200
        return jsonify({"success": False, "erro": "Formulário não encontrado"}), 404
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao obter formulário: {str(e)}"}), 500

@formularios_bp.route("", methods=["POST", "OPTIONS"])
def criar_formulario():
    if request.method == "OPTIONS":
        return ("", 200)

    dados = request.get_json() or {}
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    # validação básica requerida
    required = ["data", "idagente", "tipo_inseto"]
    erros_campo = {}
    for campo in required:
        if not dados.get(campo):
            erros_campo[campo] = "Campo obrigatório"
    if erros_campo:
        conn.close()
        return jsonify({"success": False, "errors": erros_campo}), 400

    # CORREÇÃO CRÍTICA: Converter strings vazias para None nos campos de hora
    hora_inicio = dados.get('hora_inicio')
    hora_saida = dados.get('hora_saida')

    # Se for string vazia, converter para None (NULL no banco)
    if hora_inicio == "":
        hora_inicio = None
    if hora_saida == "":
        hora_saida = None

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO formularioporcasa (
                    data, bairro, endereco, tipo_inseto, hora_inicio, hora_saida,
                    num_pontos_criticos, total_criaduros_encontrados, criaduros_eliminados, tipos_criaduros,
                    num_locos_larva, num_locos_positivos, num_adultos_encontrados,
                    num_adultos_coletados, acaorealizada, inseticida_usado,
                    quantidade_inseticida, casos_suspeitos, nome_pessoa,
                    telefone_pessoa, observacoes, idagente
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING idboletimdiario;
            """, (
                dados.get('data'), 
                dados.get('bairro', ''),
                dados.get('endereco', ''),
                dados.get('tipo_inseto'),
                hora_inicio,  # Agora pode ser None em vez de string vazia
                hora_saida,   # Agora pode ser None em vez de string vazia
                dados.get('num_pontos_criticos', 0),
                dados.get('total_criaduros_encontrados', 0),
                dados.get('criaduros_eliminados', 0),
                dados.get('tipos_criaduros', ''),
                dados.get('num_locos_larva', 0),
                dados.get('num_locos_positivos', 0),
                dados.get('num_adultos_encontrados', 0),
                dados.get('num_adultos_coletados', 0),
                dados.get('acaorealizada', ''),
                dados.get('inseticida_usado', ''),
                dados.get('quantidade_inseticida', ''),
                dados.get('casos_suspeitos', 0),
                dados.get('nome_pessoa', ''),
                dados.get('telefone_pessoa', ''),
                dados.get('observacoes', ''),
                dados.get('idagente')
            ))
            novo_id = cursor.fetchone()[0]

            # Atualiza resumo diário (remoção e inserção com agregação)
            cursor.execute("""
                DELETE FROM resumodiario 
                WHERE data = %s AND idagente = %s;
                INSERT INTO resumodiario (
                    data, idagente, total_domicilios_visitados, total_pontos_criticos,
                    total_criaduros_encontrados, total_criaduros_eliminados,
                    total_larvas_encontradas, total_larvas_coletadas,
                    total_adultos_coletados, total_casos_suspeitos
                )
                SELECT 
                    data, idagente, COUNT(*) as total_domicilios_visitados,
                    SUM(COALESCE(num_pontos_criticos,0)) as total_pontos_criticos,
                    SUM(COALESCE(total_criaduros_encontrados,0)) as total_criaduros_encontrados,
                    SUM(COALESCE(criaduros_eliminados,0)) as total_criaduros_eliminados,
                    SUM(COALESCE(num_locos_larva,0)) as total_larvas_encontradas,
                    SUM(COALESCE(num_locos_positivos,0)) as total_larvas_coletadas,
                    SUM(COALESCE(num_adultos_coletados,0)) as total_adultos_coletados,
                    SUM(COALESCE(casos_suspeitos,0)) as total_casos_suspeitos
                FROM formularioporcasa 
                WHERE data = %s AND idagente = %s
                GROUP BY data, idagente;
            """, (dados.get('data'), dados.get('idagente'), dados.get('data'), dados.get('idagente')))

        conn.commit()
        conn.close()
        return jsonify({
            "success": True,
            "mensagem": "Formulário criado com sucesso",
            "id_formulario": novo_id,
            "resumo_atualizado": True
        }), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao criar formulário: {str(e)}"}), 500

@formularios_bp.route("/resumo/diario", methods=["GET"])
def resumo_diario():
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT data, COUNT(*) as total_formularios,
                       SUM(num_pontos_criticos) as total_pontos_criticos,
                       SUM(total_criaduros_encontrados) as total_criaduros_encontrados,
                       SUM(criaduros_eliminados) as total_criaduros_eliminados
                FROM formularioporcasa
                GROUP BY data
                ORDER BY data DESC;
            """)
            resumo = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "data": resumo}), 200
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao buscar resumo diário: {str(e)}"}), 500