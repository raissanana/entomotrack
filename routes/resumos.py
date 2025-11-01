from flask import Blueprint, jsonify
from database import get_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

resumos_bp = Blueprint('resumos', __name__)

@resumos_bp.route('/diarios', methods=['GET'])
def resumos_diarios():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM resumodiario ORDER BY data DESC;")
    resumos = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(resumos)

@resumos_bp.route('/semanais', methods=['GET'])
def resumos_semanais():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM resumosemanal ORDER BY data_inicio DESC;")
    resumos = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(resumos)

@resumos_bp.route('/mensais', methods=['GET'])
def resumos_mensais():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM resumomensal ORDER BY data_inicio DESC;")
    resumos = cursor.fetchall()
    cursor.close()
    connection.close()
    return jsonify(resumos)

@resumos_bp.route('/gerar-semanais', methods=['POST'])
def gerar_resumos_semanais():
    """Gera resumos semanais a partir dos resumos diários"""
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        # Calcula semana atual (segunda a domingo)
        hoje = datetime.now().date()
        inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda-feira
        fim_semana = inicio_semana + timedelta(days=6)  # Domingo
        
        cursor.execute("""
            INSERT INTO resumosemanal (
                data_inicio, data_fim, idagente,
                total_visitas_semana, total_pontos_criticos_semana,
                total_criaduros_semana, total_locos_larva_semana,
                total_locos_positivos_semana, total_adultos_coletados_semana,
                total_casos_suspeitos_semana
            )
            SELECT 
                %s as data_inicio,
                %s as data_fim,
                idagente,
                SUM(total_visitas) as total_visitas_semana,
                SUM(total_pontos_criticos) as total_pontos_criticos_semana,
                SUM(total_criaduros) as total_criaduros_semana,
                SUM(total_locos_larva) as total_locos_larva_semana,
                SUM(total_locos_positivos) as total_locos_positivos_semana,
                SUM(total_adultos_coletados) as total_adultos_coletados_semana,
                SUM(total_casos_suspeitos) as total_casos_suspeitos_semana
            FROM resumodiario 
            WHERE data BETWEEN %s AND %s
            GROUP BY idagente
            ON CONFLICT (data_inicio, idagente) DO UPDATE SET
                total_visitas_semana = EXCLUDED.total_visitas_semana,
                total_pontos_criticos_semana = EXCLUDED.total_pontos_criticos_semana,
                total_criaduros_semana = EXCLUDED.total_criaduros_semana,
                total_locos_larva_semana = EXCLUDED.total_locos_larva_semana,
                total_locos_positivos_semana = EXCLUDED.total_locos_positivos_semana,
                total_adultos_coletados_semana = EXCLUDED.total_adultos_coletados_semana,
                total_casos_suspeitos_semana = EXCLUDED.total_casos_suspeitos_semana;
        """, (inicio_semana, fim_semana, inicio_semana, fim_semana))
        
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({
            "mensagem": f"Resumos semanais gerados para {inicio_semana} a {fim_semana}",
            "semana": f"{inicio_semana} a {fim_semana}"
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar resumos semanais: {str(e)}"}), 500

@resumos_bp.route('/gerar-mensais', methods=['POST'])
def gerar_resumos_mensais():
    """Gera resumos mensais a partir dos resumos semanais"""
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        # Calcula mês atual
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1)  # Primeiro dia do mês
        # Último dia do mês
        if hoje.month == 12:
            fim_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        
        cursor.execute("""
            INSERT INTO resumomensal (
                data_inicio, data_fim, idagente,
                total_domicilios_visitados_mes, total_pontos_criticos_mes,
                total_criaduros_encontrados_mes, total_criaduros_eliminados_mes,
                total_larvas_encontradas_mes, total_larvas_coletadas_mes,
                total_adultos_coletados_mes, total_casos_suspeitos_mes
            )
            SELECT 
                %s as data_inicio,
                %s as data_fim,
                idagente,
                SUM(total_visitas_semana) as total_domicilios_visitados_mes,
                SUM(total_pontos_criticos_semana) as total_pontos_criticos_mes,
                SUM(total_criaduros_semana) as total_criaduros_encontrados_mes,
                SUM(total_criaduros_semana) as total_criaduros_eliminados_mes,  # Ajuste conforme sua lógica
                SUM(total_locos_larva_semana) as total_larvas_encontradas_mes,
                SUM(total_locos_positivos_semana) as total_larvas_coletadas_mes,
                SUM(total_adultos_coletados_semana) as total_adultos_coletados_mes,
                SUM(total_casos_suspeitos_semana) as total_casos_suspeitos_mes
            FROM resumosemanal 
            WHERE data_inicio BETWEEN %s AND %s
            GROUP BY idagente
            ON CONFLICT (data_inicio, idagente) DO UPDATE SET
                total_domicilios_visitados_mes = EXCLUDED.total_domicilios_visitados_mes,
                total_pontos_criticos_mes = EXCLUDED.total_pontos_criticos_mes,
                total_criaduros_encontrados_mes = EXCLUDED.total_criaduros_encontrados_mes,
                total_criaduros_eliminados_mes = EXCLUDED.total_criaduros_eliminados_mes,
                total_larvas_encontradas_mes = EXCLUDED.total_larvas_encontradas_mes,
                total_larvas_coletadas_mes = EXCLUDED.total_larvas_coletadas_mes,
                total_adultos_coletados_mes = EXCLUDED.total_adultos_coletados_mes,
                total_casos_suspeitos_mes = EXCLUDED.total_casos_suspeitos_mes;
        """, (inicio_mes, fim_mes, inicio_mes, fim_mes))
        
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({
            "mensagem": f"Resumos mensais gerados para {inicio_mes.strftime('%B %Y')}",
            "mes": inicio_mes.strftime("%B %Y"),
            "periodo": f"{inicio_mes} a {fim_mes}"
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar resumos mensais: {str(e)}"}), 500

@resumos_bp.route('/gerar-todos', methods=['POST'])
def gerar_todos_resumos():
    """Gera todos os resumos (diários, semanais e mensais)"""
    try:
        # Primeiro gera semanais
        resultado_semanais = gerar_resumos_semanais()
        
        # Depois gera mensais
        resultado_mensais = gerar_resumos_mensais()
        
        return jsonify({
            "mensagem": "Todos os resumos gerados com sucesso",
            "semanais": resultado_semanais.get_json(),
            "mensais": resultado_mensais.get_json()
        }), 201
        
    except Exception as e:
        return jsonify({"erro": f"Erro ao gerar todos os resumos: {str(e)}"}), 500