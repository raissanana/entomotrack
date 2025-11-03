from flask import Blueprint, request, jsonify
from database import get_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import json

resumos_bp = Blueprint('resumos', __name__)

# === ROTAS EXISTENTES PARA BUSCAR RESUMOS ===
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

# === ROTAS PARA GERAR RESUMOS AUTOMÁTICOS ===
@resumos_bp.route('/gerar-semanais', methods=['POST'])
def gerar_resumos_semanais():
    """Gera resumos semanais a partir dos resumos diários"""
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        # Calcula semana atual (segunda a domingo)
        hoje = datetime.now().date()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        # DEBUG: Verifica se existem resumos diários para essa semana
        cursor.execute("SELECT COUNT(*) as total FROM resumodiario WHERE data BETWEEN %s AND %s", 
                      (inicio_semana, fim_semana))
        total_diarios = cursor.fetchone()[0]
        print(f"📊 Resumos diários encontrados para a semana: {total_diarios}")
        
        cursor.execute("""
            DELETE FROM resumosemanal WHERE data_inicio = %s;
            
            INSERT INTO resumosemanal (
                data_inicio, data_fim, idagente,
                total_domicilios_visitados, total_pontos_criticos,
                total_criaduros_encontrados, total_criaduros_eliminados,
                total_larvas_encontradas, total_larvas_coletadas,
                total_adultos_coletados, total_casos_suspeitos
            )
            SELECT 
                %s, %s, idagente,
                SUM(total_domicilios_visitados),
                SUM(total_pontos_criticos),
                SUM(total_criaduros_encontrados),
                SUM(total_criaduros_eliminados),
                SUM(total_larvas_encontradas),
                SUM(total_larvas_coletadas),
                SUM(total_adultos_coletados),
                SUM(total_casos_suspeitos)
            FROM resumodiario 
            WHERE data BETWEEN %s AND %s
            GROUP BY idagente;
        """, (inicio_semana, inicio_semana, fim_semana, inicio_semana, fim_semana))
        
        connection.commit()
        
        # Verifica se inseriu algo
        cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))
        total_inserido = cursor.fetchone()[0]
        print(f"✅ Resumos semanais inseridos: {total_inserido}")
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "mensagem": f"Resumos semanais gerados para {inicio_semana} a {fim_semana}",
            "semana": f"{inicio_semana} a {fim_semana}",
            "dados_encontrados": total_diarios,
            "resumos_gerados": total_inserido
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
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            fim_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
        
        # DEBUG: Verifica resumos semanais do mês
        cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio BETWEEN %s AND %s", 
                      (inicio_mes, fim_mes))
        total_semanais = cursor.fetchone()[0]
        print(f"📊 Resumos semanais encontrados para o mês: {total_semanais}")
        
        cursor.execute("""
            DELETE FROM resumomensal WHERE data_inicio = %s;
            
            INSERT INTO resumomensal (
                data_inicio, data_fim, idagente,
                total_domicilios_visitados_mes, total_pontos_criticos_mes,
                total_criaduros_encontrados_mes, total_criaduros_eliminados_mes,
                total_larvas_encontradas_mes, total_larvas_coletadas_mes,
                total_adultos_coletados_mes, total_casos_suspeitos_mes
            )
            SELECT 
                %s, %s, idagente,
                SUM(total_domicilios_visitados),
                SUM(total_pontos_criticos),
                SUM(total_criaduros_encontrados),
                SUM(total_criaduros_eliminados),
                SUM(total_larvas_encontradas),
                SUM(total_larvas_coletadas),
                SUM(total_adultos_coletados),
                SUM(total_casos_suspeitos)
            FROM resumosemanal 
            WHERE data_inicio BETWEEN %s AND %s
            GROUP BY idagente;
        """, (inicio_mes, inicio_mes, fim_mes, inicio_mes, fim_mes))
        
        connection.commit()
        
        # Verifica inserção
        cursor.execute("SELECT COUNT(*) as total FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
        total_inserido = cursor.fetchone()[0]
        print(f"✅ Resumos mensais inseridos: {total_inserido}")
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "mensagem": f"Resumos mensais gerados para {inicio_mes.strftime('%B %Y')}",
            "mes": inicio_mes.strftime("%B %Y"),
            "periodo": f"{inicio_mes} a {fim_mes}",
            "dados_encontrados": total_semanais,
            "resumos_gerados": total_inserido
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar resumos mensais: {str(e)}"}), 500

@resumos_bp.route('/gerar-todos', methods=['POST'])
def gerar_todos_resumos():
    """Gera todos os resumos (diários, semanais e mensais)"""
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        hoje = datetime.now().date()
        
        # 1. Gera semanais
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
        
        # 2. Gera mensais - CORREÇÃO: usar mesma lógica da função separada
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            fim_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
            
        cursor.execute("DELETE FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
        cursor.execute("""
            INSERT INTO resumomensal (
                data_inicio, data_fim, idagente,
                total_domicilios_visitados_mes, total_pontos_criticos_mes,
                total_criaduros_encontrados_mes, total_criaduros_eliminados_mes,
                total_larvas_encontradas_mes, total_larvas_coletadas_mes,
                total_adultos_coletados_mes, total_casos_suspeitos_mes
            )
            SELECT 
                %s, %s, idagente,
                SUM(total_domicilios_visitados),
                SUM(total_pontos_criticos),
                SUM(total_criaduros_encontrados),
                SUM(total_criaduros_eliminados),
                SUM(total_larvas_encontradas),
                SUM(total_larvas_coletadas),
                SUM(total_adultos_coletados),
                SUM(total_casos_suspeitos)
            FROM resumosemanal 
            WHERE data_inicio BETWEEN %s AND %s
            GROUP BY idagente
        """, (inicio_mes, fim_mes, inicio_mes, fim_mes))
        
        connection.commit()
        
        # Verifica o que foi gerado
        cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))
        semanais_gerados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as total FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
        mensais_gerados = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "mensagem": "Todos os resumos gerados com sucesso",
            "semana": f"{inicio_semana} a {fim_semana}",
            "mes": inicio_mes.strftime("%B %Y"),
            "resumos_semanais_gerados": semanais_gerados,
            "resumos_mensais_gerados": mensais_gerados
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar todos os resumos: {str(e)}"}), 500

# === ROTAS PARA RESUMOS CUSTOMIZADOS ===
@resumos_bp.route('/gerar-semanal-custom', methods=['POST'])
def gerar_resumo_semanal_custom():
    """Gera resumo semanal para período escolhido pelo usuário"""
    dados = request.get_json()
    
    if not dados or 'data_inicio' not in dados or 'data_fim' not in dados:
        return jsonify({"erro": "Período não especificado. Envie data_inicio e data_fim"}), 400
    
    data_inicio = dados['data_inicio']
    data_fim = dados['data_fim']
    
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        print(f"🔍 GERANDO RESUMO SEMANAL CUSTOM: {data_inicio} a {data_fim}")
        
        # Verifica se existem resumos diários para esse período
        cursor.execute("SELECT COUNT(*) FROM resumodiario WHERE data BETWEEN %s AND %s", 
                      (data_inicio, data_fim))
        total_diarios = cursor.fetchone()[0]
        print(f"📊 Resumos diários encontrados: {total_diarios}")
        
        cursor.execute("""
            -- Primeiro deleta se já existir resumo para esse período exato
            DELETE FROM resumosemanal 
            WHERE data_inicio = %s AND data_fim = %s;
            
            -- Insere novo resumo
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
        """, (data_inicio, data_fim, data_inicio, data_fim, data_inicio, data_fim))
        
        connection.commit()
        
        # Verifica se inseriu algo
        cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio = %s AND data_fim = %s", 
                      (data_inicio, data_fim))
        total_inserido = cursor.fetchone()[0]
        print(f"✅ Resumos semanais custom inseridos: {total_inserido}")
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "mensagem": f"Resumo semanal customizado gerado para {data_inicio} a {data_fim}",
            "periodo": f"{data_inicio} a {data_fim}",
            "tipo": "customizado",
            "dados_encontrados": total_diarios,
            "resumos_gerados": total_inserido
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar resumo semanal customizado: {str(e)}"}), 500

@resumos_bp.route('/gerar-mensal-custom', methods=['POST'])
def gerar_resumo_mensal_custom():
    """Gera resumo mensal para mês/ano escolhido pelo usuário"""
    dados = request.get_json()
    
    if not dados or 'mes' not in dados or 'ano' not in dados:
        return jsonify({"erro": "Mês e ano não especificados. Envie mes e ano"}), 400
    
    mes = int(dados['mes'])
    ano = int(dados['ano'])
    
    # Calcular período do mês
    data_inicio = f"{ano}-{mes:02d}-01"
    
    if mes == 12:
        data_fim = f"{ano}-12-31"
    else:
        # Último dia do mês
        proximo_mes = mes + 1
        data_fim = f"{ano}-{proximo_mes:02d}-01"
        # Ajusta para o último dia do mês atual
        data_fim = (datetime.strptime(data_fim, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        print(f"🔍 GERANDO RESUMO MENSAL CUSTOM: {data_inicio} a {data_fim}")
        
        # Verifica resumos semanais do mês
        cursor.execute("SELECT COUNT(*) FROM resumosemanal WHERE data_inicio BETWEEN %s AND %s", 
                      (data_inicio, data_fim))
        total_semanais = cursor.fetchone()[0]
        print(f"📊 Resumos semanais encontrados: {total_semanais}")
        
        cursor.execute("""
            -- Primeiro deleta se já existir resumo para esse mês
            DELETE FROM resumomensal WHERE data_inicio = %s;
            
            -- Insere novo resumo
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
        """, (data_inicio, data_inicio, data_fim, data_inicio, data_fim))
        
        connection.commit()
        
        # Verifica inserção
        cursor.execute("SELECT COUNT(*) as total FROM resumomensal WHERE data_inicio = %s", (data_inicio,))
        total_inserido = cursor.fetchone()[0]
        print(f"✅ Resumos mensais custom inseridos: {total_inserido}")
        
        cursor.close()
        connection.close()
        
        nome_mes = datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%B')
        
        return jsonify({
            "mensagem": f"Resumo mensal customizado gerado para {nome_mes} de {ano}",
            "mes": nome_mes,
            "ano": ano,
            "periodo": f"{data_inicio} a {data_fim}",
            "tipo": "customizado",
            "dados_encontrados": total_semanais,
            "resumos_gerados": total_inserido
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar resumo mensal customizado: {str(e)}"}), 500

# === ROTAS PARA BUSCAR RESUMOS CUSTOMIZADOS ===
@resumos_bp.route('/semanais-custom', methods=['GET'])
def resumos_semanais_custom():
    """Busca todos os resumos semanais customizados"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM resumosemanal 
            ORDER BY data_inicio DESC, data_fim DESC;
        """)
        resumos = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({
            "tipo": "semanais_customizados",
            "total": len(resumos),
            "dados": resumos
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao buscar resumos semanais customizados: {str(e)}"}), 500

@resumos_bp.route('/mensais-custom', methods=['GET'])
def resumos_mensais_custom():
    """Busca todos os resumos mensais customizados"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM resumomensal 
            ORDER BY data_inicio DESC;
        """)
        resumos = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({
            "tipo": "mensais_customizados",
            "total": len(resumos),
            "dados": resumos
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao buscar resumos mensais customizados: {str(e)}"}), 500

# === ROTAS PARA BUSCAR RESUMOS POR PERÍODO ESPECÍFICO ===
@resumos_bp.route('/semanais/periodo', methods=['GET'])
def resumos_semanais_por_periodo():
    """Busca resumos semanais por período específico"""
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    if not data_inicio or not data_fim:
        return jsonify({"erro": "Parâmetros data_inicio e data_fim são obrigatórios"}), 400
    
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM resumosemanal 
            WHERE data_inicio = %s AND data_fim = %s
            ORDER BY idagente;
        """, (data_inicio, data_fim))
        
        resumos = cursor.fetchall()
        cursor.close()
        connection.close()
        
        return jsonify({
            "periodo": f"{data_inicio} a {data_fim}",
            "total": len(resumos),
            "dados": resumos
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao buscar resumos do período: {str(e)}"}), 500

@resumos_bp.route('/mensais/mes', methods=['GET'])
def resumos_mensais_por_mes():
    """Busca resumos mensais por mês/ano específico"""
    mes = request.args.get('mes')
    ano = request.args.get('ano')
    
    if not mes or not ano:
        return jsonify({"erro": "Parâmetros mes e ano são obrigatórios"}), 400
    
    data_inicio = f"{ano}-{mes:02d}-01"
    
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM resumomensal 
            WHERE data_inicio = %s
            ORDER BY idagente;
        """, (data_inicio,))
        
        resumos = cursor.fetchall()
        cursor.close()
        connection.close()
        
        nome_mes = datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%B')
        
        return jsonify({
            "mes": nome_mes,
            "ano": ano,
            "total": len(resumos),
            "dados": resumos
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao buscar resumos do mês: {str(e)}"}), 500

# === ROTAS PARA GRÁFICOS ===
@resumos_bp.route('/graficos/semanal/<data_inicio>/<data_fim>', methods=['GET'])
def grafico_semanal(data_inicio, data_fim):
    """Gera gráfico para resumo semanal específico"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Busca dados do período
        cursor.execute("""
            SELECT * FROM resumosemanal 
            WHERE data_inicio = %s AND data_fim = %s
        """, (data_inicio, data_fim))
        
        dados = cursor.fetchall()
        
        if not dados:
            return jsonify({"erro": "Nenhum dado encontrado para o período"}), 404
        
        # Prepara dados para gráfico
        agentes = [f"Agente {d['idagente']}" for d in dados]
        visitas = [d['total_domicilios_visitados'] for d in dados]
        criaduros = [d['total_criaduros_encontrados'] for d in dados]
        larvas = [d['total_larvas_encontradas'] for d in dados]
        pontos_criticos = [d['total_pontos_criticos'] for d in dados]
        
        # Gráfico 1: Barras comparativas
        fig_barras = go.Figure()
        
        fig_barras.add_trace(go.Bar(
            name='Domicílios Visitados',
            x=agentes,
            y=visitas,
            marker_color='#1f77b4'
        ))
        
        fig_barras.add_trace(go.Bar(
            name='Criaduros Encontrados',
            x=agentes,
            y=criaduros,
            marker_color='#ff7f0e'
        ))
        
        fig_barras.add_trace(go.Bar(
            name='Larvas Encontradas',
            x=agentes,
            y=larvas,
            marker_color='#2ca02c'
        ))
        
        fig_barras.update_layout(
            title=f'Desempenho dos Agentes - {data_inicio} a {data_fim}',
            xaxis_title='Agentes',
            yaxis_title='Quantidade',
            barmode='group',
            template='plotly_white'
        )
        
        # Gráfico 2: Pizza - Distribuição de pontos críticos
        fig_pizza = px.pie(
            values=pontos_criticos,
            names=agentes,
            title=f'Distribuição de Pontos Críticos - {data_inicio} a {data_fim}',
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "periodo": f"{data_inicio} a {data_fim}",
            "graficos": {
                "barras_comparativas": json.loads(fig_barras.to_json()),
                "distribuicao_pontos_criticos": json.loads(fig_pizza.to_json())
            },
            "dados_brutos": dados
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar gráfico: {str(e)}"}), 500

@resumos_bp.route('/graficos/mensal/<mes>/<ano>', methods=['GET'])
def grafico_mensal(mes, ano):
    """Gera gráfico para resumo mensal específico"""
    data_inicio = f"{ano}-{mes}-01"
    
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT * FROM resumomensal WHERE data_inicio = %s", (data_inicio,))
        dados = cursor.fetchall()
        
        if not dados:
            return jsonify({"erro": "Nenhum dado encontrado para o mês"}), 404
        
        # Prepara dados
        agentes = [f"Agente {d['idagente']}" for d in dados]
        visitas = [d['total_domicilios_visitados_mes'] for d in dados]
        criaduros = [d['total_criaduros_encontrados_mes'] for d in dados]
        larvas = [d['total_larvas_encontradas_mes'] for d in dados]
        casos_suspeitos = [d['total_casos_suspeitos_mes'] for d in dados]
        
        nome_mes = datetime.strptime(data_inicio, '%Y-%m-%d').strftime('%B')
        
        # Gráfico 1: Barras horizontais
        fig_barras = go.Figure()
        
        fig_barras.add_trace(go.Bar(
            y=agentes,
            x=visitas,
            name='Visitas',
            orientation='h',
            marker_color='#1f77b4'
        ))
        
        fig_barras.add_trace(go.Bar(
            y=agentes,
            x=criaduros,
            name='Criaduros',
            orientation='h',
            marker_color='#ff7f0e'
        ))
        
        fig_barras.update_layout(
            title=f'Atividades Mensais - {nome_mes} {ano}',
            xaxis_title='Quantidade',
            yaxis_title='Agentes',
            barmode='stack',
            template='plotly_white'
        )
        
        # Gráfico 2: Linha para casos suspeitos
        fig_linha = px.line(
            x=agentes,
            y=casos_suspeitos,
            title=f'Casos Suspeitos por Agente - {nome_mes} {ano}',
            markers=True
        )
        
        fig_linha.update_layout(
            xaxis_title='Agentes',
            yaxis_title='Casos Suspeitos'
        )
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "mes": nome_mes,
            "ano": ano,
            "graficos": {
                "barras_horizontais": json.loads(fig_barras.to_json()),
                "linha_casos_suspeitos": json.loads(fig_linha.to_json())
            },
            "dados_brutos": dados
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar gráfico mensal: {str(e)}"}), 500

@resumos_bp.route('/graficos/comparativo-mensal', methods=['GET'])
def grafico_comparativo_mensal():
    """Gráfico comparativo dos últimos 3 meses"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Busca últimos 3 meses
        cursor.execute("""
            SELECT DISTINCT data_inicio 
            FROM resumomensal 
            ORDER BY data_inicio DESC 
            LIMIT 3
        """)
        
        meses = cursor.fetchall()
        
        if not meses:
            return jsonify({"erro": "Nenhum dado mensal encontrado"}), 404
        
        dados_comparativos = []
        
        for mes in meses:
            data_inicio = mes['data_inicio']
            cursor.execute("""
                SELECT 
                    data_inicio,
                    SUM(total_domicilios_visitados_mes) as total_visitas,
                    SUM(total_criaduros_encontrados_mes) as total_criaduros,
                    SUM(total_larvas_encontradas_mes) as total_larvas
                FROM resumomensal 
                WHERE data_inicio = %s
                GROUP BY data_inicio
            """, (data_inicio,))
            
            dados_mes = cursor.fetchone()
            if dados_mes:
                dados_comparativos.append(dados_mes)
        
        # Prepara dados para gráfico
        meses_nomes = [datetime.strptime(str(d['data_inicio']), '%Y-%m-%d').strftime('%b/%Y') for d in dados_comparativos]
        visitas = [d['total_visitas'] for d in dados_comparativos]
        criaduros = [d['total_criaduros'] for d in dados_comparativos]
        larvas = [d['total_larvas'] for d in dados_comparativos]
        
        # Gráfico de linhas comparativo
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=meses_nomes,
            y=visitas,
            name='Visitas',
            line=dict(color='blue', width=3),
            mode='lines+markers'
        ))
        
        fig.add_trace(go.Scatter(
            x=meses_nomes,
            y=criaduros,
            name='Criaduros',
            line=dict(color='red', width=3),
            mode='lines+markers'
        ))
        
        fig.add_trace(go.Scatter(
            x=meses_nomes,
            y=larvas,
            name='Larvas',
            line=dict(color='green', width=3),
            mode='lines+markers'
        ))
        
        fig.update_layout(
            title='Comparativo dos Últimos 3 Meses',
            xaxis_title='Meses',
            yaxis_title='Quantidade',
            template='plotly_white'
        )
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "grafico": json.loads(fig.to_json()),
            "periodos": meses_nomes,
            "dados_comparativos": dados_comparativos
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar gráfico comparativo: {str(e)}"}), 500

@resumos_bp.route('/graficos/estatisticas-gerais', methods=['GET'])
def estatisticas_gerais():
    """Estatísticas gerais e gráficos consolidados"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Estatísticas totais
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT idagente) as total_agentes,
                SUM(total_domicilios_visitados_mes) as total_visitas,
                SUM(total_criaduros_encontrados_mes) as total_criaduros,
                SUM(total_larvas_encontradas_mes) as total_larvas,
                SUM(total_casos_suspeitos_mes) as total_casos_suspeitos
            FROM resumomensal 
            WHERE data_inicio = (SELECT MAX(data_inicio) FROM resumomensal)
        """)
        
        estatisticas = cursor.fetchone()
        
        # Top agentes
        cursor.execute("""
            SELECT 
                idagente,
                total_domicilios_visitados_mes as visitas
            FROM resumomensal 
            WHERE data_inicio = (SELECT MAX(data_inicio) FROM resumomensal)
            ORDER BY visitas DESC 
            LIMIT 5
        """)
        
        top_agentes = cursor.fetchall()
        
        # Gráfico de dashboard
        fig = go.Figure()
        
        categorias = ['Visitas', 'Criaduros', 'Larvas', 'Casos Suspeitos']
        valores = [
            estatisticas['total_visitas'] or 0,
            estatisticas['total_criaduros'] or 0,
            estatisticas['total_larvas'] or 0,
            estatisticas['total_casos_suspeitos'] or 0
        ]
        
        fig.add_trace(go.Bar(
            x=categorias,
            y=valores,
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        ))
        
        fig.update_layout(
            title='Estatísticas Gerais - Último Mês',
            template='plotly_white'
        )
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "estatisticas": estatisticas,
            "top_agentes": top_agentes,
            "grafico_estatisticas": json.loads(fig.to_json())
        }), 200
        
    except Exception as e:
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar estatísticas: {str(e)}"}), 500