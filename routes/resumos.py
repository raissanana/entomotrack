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
            -- Primeiro deleta resumos existentes para essa semana
            DELETE FROM resumosemanal WHERE data_inicio = %s;
            
            -- Depois insere os novos resumos
            INSERT INTO resumosemanal (
                data_inicio, data_fim, idagente,
                total_domicilios_visitados, total_pontos_criticos,
                total_criaduros_encontrados, total_criaduros_eliminados,
                total_larvas_encontradas, total_larvas_coletadas,
                total_adultos_coletados, total_casos_suspeitos
            )
            SELECT 
                %s as data_inicio,
                %s as data_fim,
                idagente,
                SUM(total_domicilios_visitados) as total_domicilios_visitados,
                SUM(total_pontos_criticos) as total_pontos_criticos,
                SUM(total_criaduros_encontrados) as total_criaduros_encontrados,
                SUM(total_criaduros_eliminados) as total_criaduros_eliminados,
                SUM(total_larvas_encontradas) as total_larvas_encontradas,
                SUM(total_larvas_coletadas) as total_larvas_coletadas,
                SUM(total_adultos_coletados) as total_adultos_coletados,
                SUM(total_casos_suspeitos) as total_casos_suspeitos
            FROM resumodiario 
            WHERE data BETWEEN %s AND %s
            GROUP BY idagente;
        """, (inicio_semana, inicio_semana, fim_semana, inicio_semana, fim_semana))
        
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
            -- Primeiro deleta resumos existentes para esse mês
            DELETE FROM resumomensal WHERE data_inicio = %s;
            
            -- Depois insere os novos resumos
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
                SUM(total_domicilios_visitados) as total_domicilios_visitados_mes,
                SUM(total_pontos_criticos) as total_pontos_criticos_mes,
                SUM(total_criaduros_encontrados) as total_criaduros_encontrados_mes,
                SUM(total_criaduros_eliminados) as total_criaduros_eliminados_mes,
                SUM(total_larvas_encontradas) as total_larvas_encontradas_mes,
                SUM(total_larvas_coletadas) as total_larvas_coletadas_mes,
                SUM(total_adultos_coletados) as total_adultos_coletados_mes,
                SUM(total_casos_suspeitos) as total_casos_suspeitos_mes
            FROM resumosemanal 
            WHERE data_inicio BETWEEN %s AND %s
            GROUP BY idagente;
        """, (inicio_mes, inicio_mes, fim_mes, inicio_mes, fim_mes))
        
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
        # Gera semanais
        cursor = get_connection().cursor()
        hoje = datetime.now().date()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        cursor.execute("DELETE FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))
        cursor.execute("""
            INSERT INTO resumosemanal (
                data_inicio, data_fim, idagente, total_domicilios_visitados,
                total_pontos_criticos, total_criaduros_encontrados, total_criaduros_eliminados,
                total_larvas_encontradas, total_larvas_coletadas, total_adultos_coletados,
                total_casos_suspeitos
            )
            SELECT 
                %s, %s, idagente,
                SUM(total_domicilios_visitados), SUM(total_pontos_criticos),
                SUM(total_criaduros_encontrados), SUM(total_criaduros_eliminados),
                SUM(total_larvas_encontradas), SUM(total_larvas_coletadas),
                SUM(total_adultos_coletados), SUM(total_casos_suspeitos)
            FROM resumodiario 
            WHERE data BETWEEN %s AND %s
            GROUP BY idagente
        """, (inicio_semana, fim_semana, inicio_semana, fim_semana))
        
        # Gera mensais
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            fim_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
            
        cursor.execute("DELETE FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
        cursor.execute("""
            INSERT INTO resumomensal (
                data_inicio, data_fim, idagente, total_domicilios_visitados_mes,
                total_pontos_criticos_mes, total_criaduros_encontrados_mes, total_criaduros_eliminados_mes,
                total_larvas_encontradas_mes, total_larvas_coletadas_mes, total_adultos_coletados_mes,
                total_casos_suspeitos_mes
            )
            SELECT 
                %s, %s, idagente,
                SUM(total_domicilios_visitados), SUM(total_pontos_criticos),
                SUM(total_criaduros_encontrados), SUM(total_criaduros_eliminados),
                SUM(total_larvas_encontradas), SUM(total_larvas_coletadas),
                SUM(total_adultos_coletados), SUM(total_casos_suspeitos)
            FROM resumosemanal 
            WHERE data_inicio BETWEEN %s AND %s
            GROUP BY idagente
        """, (inicio_mes, fim_mes, inicio_mes, fim_mes))
        
        get_connection().commit()
        cursor.close()
        get_connection().close()
        
        return jsonify({
            "mensagem": "Todos os resumos gerados com sucesso",
            "semana": f"{inicio_semana} a {fim_semana}",
            "mes": inicio_mes.strftime("%B %Y")
        }), 201
        
    except Exception as e:
        get_connection().rollback()
        cursor.close()
        get_connection().close()
        return jsonify({"erro": f"Erro ao gerar todos os resumos: {str(e)}"}), 500