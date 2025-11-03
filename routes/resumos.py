from flask import Blueprint, request, jsonify, Response
from database import get_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import json
import plotly.io as pio
import zipfile
from io import BytesIO

resumos_bp = Blueprint('resumos', __name__)

# Rotas para buscar resumos existentes
@resumos_bp.route('/diarios', methods=['GET'])
def resumos_diarios():
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM resumodiario ORDER BY data DESC;")
            resumos = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "data": resumos}), 200
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao buscar resumos diários: {str(e)}"}), 500

@resumos_bp.route('/semanais', methods=['GET'])
def resumos_semanais():
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM resumosemanal ORDER BY data_inicio DESC;")
            resumos = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "data": resumos}), 200
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao buscar resumos semanais: {str(e)}"}), 500

@resumos_bp.route('/mensais', methods=['GET'])
def resumos_mensais():
    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM resumomensal ORDER BY data_inicio DESC;")
            resumos = cursor.fetchall()
        conn.close()
        return jsonify({"success": True, "data": resumos}), 200
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao buscar resumos mensais: {str(e)}"}), 500

# Rota para gerar resumos diários
@resumos_bp.route('/gerar-diarios', methods=['POST'])
def gerar_resumos_diarios():
    data = request.get_json()
    
    if not data or 'data' not in data:
        return jsonify({"success": False, "erro": "Data é obrigatória"}), 400
    
    try:
        data_selecionada = datetime.strptime(data['data'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor() as cursor:
            # Verificar se já existe resumo diário para esta data
            cursor.execute("SELECT COUNT(*) as total FROM resumodiario WHERE data = %s", (data_selecionada,))
            total_existente = cursor.fetchone()[0]
            
            if total_existente > 0:
                acao = data.get('acao', 'manter')
                if acao == 'pular':
                    conn.close()
                    return jsonify({
                        "success": True,
                        "mensagem": f"Resumo diário já existe para {data_selecionada}. Ação: pular"
                    }), 200
                elif acao == 'sobrescrever':
                    cursor.execute("DELETE FROM resumodiario WHERE data = %s", (data_selecionada,))

            # Inserir dados de exemplo
            cursor.execute("""
                INSERT INTO resumodiario (
                    data, idagente, total_domicilios_visitados, total_pontos_criticos,
                    total_criaduros_encontrados, total_criaduros_eliminados,
                    total_larvas_encontradas, total_larvas_coletadas,
                    total_adultos_coletados, total_casos_suspeitos
                ) VALUES 
                (%s, 1, 15, 3, 8, 6, 12, 9, 7, 2),
                (%s, 2, 12, 2, 5, 4, 8, 6, 5, 1),
                (%s, 3, 18, 4, 10, 8, 15, 12, 9, 3)
            """, (data_selecionada, data_selecionada, data_selecionada))

            conn.commit()

            cursor.execute("SELECT COUNT(*) as total FROM resumodiario WHERE data = %s", (data_selecionada,))
            total_inserido = cursor.fetchone()[0]

        conn.close()
        return jsonify({
            "success": True,
            "mensagem": f"Resumo diário gerado para {data_selecionada}",
            "data": data_selecionada.isoformat(),
            "resumos_gerados": total_inserido
        }), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar resumo diário: {str(e)}"}), 500

# Rota para gerar resumos semanais
@resumos_bp.route('/gerar-semanais', methods=['POST'])
def gerar_resumos_semanais():
    data = request.get_json()
    
    if not data or 'data_referencia' not in data:
        return jsonify({"success": False, "erro": "Data de referência é obrigatória"}), 400
    
    try:
        data_referencia = datetime.strptime(data['data_referencia'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        inicio_semana = data_referencia - timedelta(days=data_referencia.weekday())
        fim_semana = inicio_semana + timedelta(days=6)

        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM resumodiario WHERE data BETWEEN %s AND %s", 
                         (inicio_semana, fim_semana))
            total_diarios = cursor.fetchone()[0]

            if total_diarios == 0:
                return jsonify({
                    "success": False, 
                    "erro": f"Não existem resumos diários para a semana de {inicio_semana} a {fim_semana}"
                }), 400

            cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))
            total_existente = cursor.fetchone()[0]

            if total_existente > 0:
                acao = data.get('acao', 'manter')
                if acao == 'pular':
                    conn.close()
                    return jsonify({
                        "success": True,
                        "mensagem": f"Resumo semanal já existe para esta semana. Ação: pular"
                    }), 200
                elif acao == 'sobrescrever':
                    cursor.execute("DELETE FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))

            cursor.execute("""
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
            """, (inicio_semana, fim_semana, inicio_semana, fim_semana))

            conn.commit()

            cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))
            total_inserido = cursor.fetchone()[0]

        conn.close()
        return jsonify({
            "success": True,
            "mensagem": f"Resumos semanais gerados para {inicio_semana} a {fim_semana}",
            "periodo": {
                "data_inicio": inicio_semana.isoformat(),
                "data_fim": fim_semana.isoformat()
            },
            "dados_encontrados": total_diarios,
            "resumos_gerados": total_inserido
        }), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar resumos semanais: {str(e)}"}), 500

# Rota para gerar resumos mensais
@resumos_bp.route('/gerar-mensais', methods=['POST'])
def gerar_resumos_mensais():
    data = request.get_json()
    
    if not data or 'data_referencia' not in data:
        return jsonify({"success": False, "erro": "Data de referência é obrigatória"}), 400
    
    try:
        data_referencia = datetime.strptime(data['data_referencia'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        inicio_mes = data_referencia.replace(day=1)
        if data_referencia.month == 12:
            fim_mes = data_referencia.replace(year=data_referencia.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = data_referencia.replace(month=data_referencia.month + 1, day=1) - timedelta(days=1)

        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio BETWEEN %s AND %s", 
                         (inicio_mes, fim_mes))
            total_semanais = cursor.fetchone()[0]

            if total_semanais == 0:
                return jsonify({
                    "success": False, 
                    "erro": f"Não existem resumos semanais para o mês de {inicio_mes.strftime('%B %Y')}"
                }), 400

            cursor.execute("SELECT COUNT(*) as total FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
            total_existente = cursor.fetchone()[0]

            if total_existente > 0:
                acao = data.get('acao', 'manter')
                if acao == 'pular':
                    conn.close()
                    return jsonify({
                        "success": True,
                        "mensagem": f"Resumo mensal já existe para este mês. Ação: pular"
                    }), 200
                elif acao == 'sobrescrever':
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
                GROUP BY idagente;
            """, (inicio_mes, fim_mes, inicio_mes, fim_mes))

            conn.commit()

            cursor.execute("SELECT COUNT(*) as total FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
            total_inserido = cursor.fetchone()[0]

        conn.close()
        return jsonify({
            "success": True,
            "mensagem": f"Resumos mensais gerados para {inicio_mes.strftime('%B %Y')}",
            "periodo": {
                "data_inicio": inicio_mes.isoformat(),
                "data_fim": fim_mes.isoformat()
            },
            "dados_encontrados": total_semanais,
            "resumos_gerados": total_inserido
        }), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar resumos mensais: {str(e)}"}), 500

# ROTAS PARA GRÁFICOS EM JSON
@resumos_bp.route('/graficos/diarios/<data>', methods=['GET'])
def grafico_diarios(data):
    """Gera gráficos para resumos diários de uma data específica"""
    try:
        data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM resumodiario 
                WHERE data = %s 
                ORDER BY idagente
            """, (data_selecionada,))
            dados = cursor.fetchall()

        if not dados:
            return jsonify({"success": False, "erro": "Nenhum dado encontrado para esta data"}), 404

        # Converter para lista de dicionários
        dados_list = [dict(row) for row in dados]

        # Gráfico 1: Comparação entre agentes (métricas principais)
        fig1 = px.bar(
            dados_list,
            x='idagente',
            y=['total_domicilios_visitados', 'total_pontos_criticos', 'total_casos_suspeitos'],
            title=f'Comparação de Agentes - {data_selecionada}',
            labels={'value': 'Quantidade', 'variable': 'Métrica', 'idagente': 'Agente'},
            barmode='group'
        )

        # Gráfico 2: Criaduros encontrados vs eliminados
        fig2 = go.Figure()
        for agente in dados_list:
            fig2.add_trace(go.Bar(
                name=f'Agente {agente["idagente"]}',
                x=['Encontrados', 'Eliminados'],
                y=[agente['total_criaduros_encontrados'], agente['total_criaduros_eliminados']],
                text=[agente['total_criaduros_encontrados'], agente['total_criaduros_eliminados']],
                textposition='auto'
            ))
        fig2.update_layout(title=f'Criaduros - {data_selecionada}', barmode='group')

        # Gráfico 3: Larvas encontradas vs coletadas
        fig3 = px.bar(
            dados_list,
            x='idagente',
            y=['total_larvas_encontradas', 'total_larvas_coletadas'],
            title=f'Larvas - {data_selecionada}',
            labels={'value': 'Quantidade', 'variable': 'Tipo'},
            barmode='group'
        )

        # Converter gráficos para JSON
        graficos_json = {
            "comparacao_agentes": json.loads(pio.to_json(fig1)),
            "criaduros": json.loads(pio.to_json(fig2)),
            "larvas": json.loads(pio.to_json(fig3)),
            "dados": dados_list
        }

        conn.close()
        return jsonify({
            "success": True,
            "data": data_selecionada.isoformat(),
            "graficos": graficos_json
        }), 200

    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar gráficos: {str(e)}"}), 500

@resumos_bp.route('/graficos/semanais/<data_inicio>', methods=['GET'])
def grafico_semanais(data_inicio):
    """Gera gráficos para resumos semanais"""
    try:
        inicio_semana = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        fim_semana = inicio_semana + timedelta(days=6)
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM resumosemanal 
                WHERE data_inicio = %s 
                ORDER BY idagente
            """, (inicio_semana,))
            dados = cursor.fetchall()

        if not dados:
            return jsonify({"success": False, "erro": "Nenhum dado encontrado para esta semana"}), 404

        dados_list = [dict(row) for row in dados]

        # Gráfico 1: Métricas principais da semana
        fig1 = px.bar(
            dados_list,
            x='idagente',
            y=['total_domicilios_visitados', 'total_pontos_criticos', 'total_casos_suspeitos'],
            title=f'Resumo Semanal - {inicio_semana} a {fim_semana}',
            labels={'value': 'Quantidade', 'variable': 'Métrica'},
            barmode='group'
        )

        # Gráfico 2: Eficiência na eliminação de criaduros
        eficiencia_data = []
        for agente in dados_list:
            if agente['total_criaduros_encontrados'] > 0:
                eficiencia = (agente['total_criaduros_eliminados'] / agente['total_criaduros_encontrados']) * 100
            else:
                eficiencia = 0
            eficiencia_data.append({
                'idagente': agente['idagente'],
                'eficiencia': round(eficiencia, 2)
            })

        fig2 = px.bar(
            eficiencia_data,
            x='idagente',
            y='eficiencia',
            title='Eficiência na Eliminação de Criaduros (%)',
            labels={'eficiencia': 'Eficiência (%)', 'idagente': 'Agente'}
        )

        # Gráfico 3: Pizza - Distribuição de atividades
        totais = {
            'Domicílios Visitados': sum([d['total_domicilios_visitados'] for d in dados_list]),
            'Pontos Críticos': sum([d['total_pontos_criticos'] for d in dados_list]),
            'Casos Suspeitos': sum([d['total_casos_suspeitos'] for d in dados_list])
        }

        fig3 = px.pie(
            values=list(totais.values()),
            names=list(totais.keys()),
            title='Distribuição de Atividades da Semana'
        )

        graficos_json = {
            "metricas_principais": json.loads(pio.to_json(fig1)),
            "eficiencia_criaduros": json.loads(pio.to_json(fig2)),
            "distribuicao_atividades": json.loads(pio.to_json(fig3)),
            "dados": dados_list,
            "periodo": {
                "inicio": inicio_semana.isoformat(),
                "fim": fim_semana.isoformat()
            }
        }

        conn.close()
        return jsonify({
            "success": True,
            "graficos": graficos_json
        }), 200

    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar gráficos semanais: {str(e)}"}), 500

@resumos_bp.route('/graficos/mensais/<data_inicio>', methods=['GET'])
def grafico_mensais(data_inicio):
    """Gera gráficos para resumos mensais"""
    try:
        inicio_mes = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if inicio_mes.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1, day=1) - timedelta(days=1)
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM resumomensal 
                WHERE data_inicio = %s 
                ORDER BY idagente
            """, (inicio_mes,))
            dados = cursor.fetchall()

        if not dados:
            return jsonify({"success": False, "erro": "Nenhum dado encontrado para este mês"}), 404

        dados_list = [dict(row) for row in dados]

        # Gráfico 1: Comparação mensal entre agentes
        fig1 = px.bar(
            dados_list,
            x='idagente',
            y=['total_domicilios_visitados_mes', 'total_pontos_criticos_mes', 'total_casos_suspeitos_mes'],
            title=f'Resumo Mensal - {inicio_mes.strftime("%B %Y")}',
            labels={'value': 'Quantidade', 'variable': 'Métrica'},
            barmode='group'
        )

        # Gráfico 2: Evolução de larvas e adultos coletados
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='Larvas Coletadas', 
                             x=[d['idagente'] for d in dados_list],
                             y=[d['total_larvas_coletadas_mes'] for d in dados_list]))
        fig2.add_trace(go.Bar(name='Adultos Coletados', 
                             x=[d['idagente'] for d in dados_list],
                             y=[d['total_adultos_coletados_mes'] for d in dados_list]))
        fig2.update_layout(title='Coleta de Larvas e Adultos', barmode='group')

        # Gráfico 3: Heatmap de produtividade
        metricas = ['Domicílios', 'Pontos Críticos', 'Criaduros Elim', 'Larvas Colet', 'Adultos Colet']
        valores = []
        for agente in dados_list:
            valores.append([
                agente['total_domicilios_visitados_mes'],
                agente['total_pontos_criticos_mes'],
                agente['total_criaduros_eliminados_mes'],
                agente['total_larvas_coletadas_mes'],
                agente['total_adultos_coletados_mes']
            ])

        fig3 = px.imshow(
            valores,
            x=metricas,
            y=[f'Agente {d["idagente"]}' for d in dados_list],
            title='Heatmap de Produtividade Mensal',
            aspect="auto",
            color_continuous_scale='Viridis'
        )

        graficos_json = {
            "comparacao_mensal": json.loads(pio.to_json(fig1)),
            "coleta_insetos": json.loads(pio.to_json(fig2)),
            "heatmap_produtividade": json.loads(pio.to_json(fig3)),
            "dados": dados_list,
            "periodo": {
                "inicio": inicio_mes.isoformat(),
                "fim": fim_mes.isoformat(),
                "mes_ano": inicio_mes.strftime("%Y-%m")
            }
        }

        conn.close()
        return jsonify({
            "success": True,
            "graficos": graficos_json
        }), 200

    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar gráficos mensais: {str(e)}"}), 500

# ROTAS PARA GRÁFICOS EM IMAGEM
@resumos_bp.route('/graficos/diarios/<data>/imagem', methods=['GET'])
def grafico_diarios_imagem(data):
    """Gera e retorna imagem PNG dos gráficos diários"""
    try:
        data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM resumodiario WHERE data = %s ORDER BY idagente", (data_selecionada,))
            dados = cursor.fetchall()

        if not dados:
            return jsonify({"success": False, "erro": "Nenhum dado encontrado para esta data"}), 404

        dados_list = [dict(row) for row in dados]

        # Gráfico principal: Comparação entre agentes
        fig = px.bar(
            dados_list,
            x='idagente',
            y=['total_domicilios_visitados', 'total_pontos_criticos', 'total_casos_suspeitos'],
            title=f'Comparação de Agentes - {data_selecionada}',
            labels={'value': 'Quantidade', 'variable': 'Métrica'},
            barmode='group'
        )

        # Converter para imagem PNG
        img_bytes = pio.to_image(fig, format='png', width=1200, height=700)

        conn.close()
        
        # Retornar a imagem
        return Response(img_bytes, mimetype='image/png')

    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar imagem: {str(e)}"}), 500

@resumos_bp.route('/graficos/diarios/<data>/zip', methods=['GET'])
def grafico_diarios_zip(data):
    """Gera ZIP com todos os gráficos do dia em PNG"""
    try:
        data_selecionada = datetime.strptime(data, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM resumodiario WHERE data = %s ORDER BY idagente", (data_selecionada,))
            dados = cursor.fetchall()

        if not dados:
            return jsonify({"success": False, "erro": "Nenhum dado encontrado para esta data"}), 404

        dados_list = [dict(row) for row in dados]

        # Criar múltiplos gráficos
        fig1 = px.bar(
            dados_list,
            x='idagente',
            y=['total_domicilios_visitados', 'total_pontos_criticos', 'total_casos_suspeitos'],
            title=f'Comparação de Agentes - {data_selecionada}',
            barmode='group'
        )

        fig2 = px.bar(
            dados_list,
            x='idagente',
            y=['total_criaduros_encontrados', 'total_criaduros_eliminados'],
            title=f'Criaduros - {data_selecionada}',
            barmode='group'
        )

        fig3 = px.bar(
            dados_list,
            x='idagente',
            y=['total_larvas_encontradas', 'total_larvas_coletadas'],
            title=f'Larvas - {data_selecionada}',
            barmode='group'
        )

        # Converter para imagens PNG
        img1_bytes = pio.to_image(fig1, format='png', width=1200, height=700)
        img2_bytes = pio.to_image(fig2, format='png', width=1200, height=700)
        img3_bytes = pio.to_image(fig3, format='png', width=1200, height=700)

        conn.close()
        
        # Criar ZIP com as imagens
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr(f'comparacao_agentes_{data}.png', img1_bytes)
            zip_file.writestr(f'criaduros_{data}.png', img2_bytes)
            zip_file.writestr(f'larvas_{data}.png', img3_bytes)
        
        zip_buffer.seek(0)
        
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={'Content-Disposition': f'attachment;filename=graficos_{data}.zip'}
        )

    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao gerar ZIP: {str(e)}"}), 500

# Rota auxiliar para verificar disponibilidade de dados
@resumos_bp.route('/verificar-disponibilidade', methods=['POST'])
def verificar_disponibilidade():
    data = request.get_json()
    
    if not data or 'tipo' not in data or 'data_referencia' not in data:
        return jsonify({"success": False, "erro": "Tipo e data de referência são obrigatórios"}), 400
    
    try:
        data_referencia = datetime.strptime(data['data_referencia'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"success": False, "erro": "Erro ao conectar ao banco"}), 500

    try:
        with conn.cursor() as cursor:
            if data['tipo'] == 'semanal':
                inicio_semana = data_referencia - timedelta(days=data_referencia.weekday())
                fim_semana = inicio_semana + timedelta(days=6)
                
                cursor.execute("SELECT COUNT(*) as total FROM resumodiario WHERE data BETWEEN %s AND %s", 
                             (inicio_semana, fim_semana))
                total_diarios = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio = %s", (inicio_semana,))
                total_semanal = cursor.fetchone()[0]
                
                conn.close()
                return jsonify({
                    "success": True,
                    "disponivel": total_diarios > 0,
                    "periodo": {
                        "data_inicio": inicio_semana.isoformat(),
                        "data_fim": fim_semana.isoformat()
                    },
                    "dados_diarios": total_diarios,
                    "resumo_existente": total_semanal > 0
                }), 200
                
            elif data['tipo'] == 'mensal':
                inicio_mes = data_referencia.replace(day=1)
                if data_referencia.month == 12:
                    fim_mes = data_referencia.replace(year=data_referencia.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    fim_mes = data_referencia.replace(month=data_referencia.month + 1, day=1) - timedelta(days=1)
                
                cursor.execute("SELECT COUNT(*) as total FROM resumosemanal WHERE data_inicio BETWEEN %s AND %s", 
                             (inicio_mes, fim_mes))
                total_semanais = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) as total FROM resumomensal WHERE data_inicio = %s", (inicio_mes,))
                total_mensal = cursor.fetchone()[0]
                
                conn.close()
                return jsonify({
                    "success": True,
                    "disponivel": total_semanais > 0,
                    "periodo": {
                        "data_inicio": inicio_mes.isoformat(),
                        "data_fim": fim_mes.isoformat()
                    },
                    "dados_semanais": total_semanais,
                    "resumo_existente": total_mensal > 0
                }), 200
            else:
                conn.close()
                return jsonify({"success": False, "erro": "Tipo inválido. Use 'semanal' ou 'mensal'"}), 400

    except Exception as e:
        conn.close()
        return jsonify({"success": False, "erro": f"Erro ao verificar disponibilidade: {str(e)}"}), 500