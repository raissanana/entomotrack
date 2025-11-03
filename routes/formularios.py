from flask import Blueprint, request, jsonify
from database import get_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime

formularios_bp = Blueprint('formularios', __name__)

@formularios_bp.route('/', methods=['GET'])
def listar_formularios():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT f.*, ag.matricula AS agente_matricula
        FROM formularioporcasa f
        JOIN agente ag ON f.idagente = ag.idagente
        ORDER BY f.data DESC;
    """)
    formularios = cursor.fetchall()
    cursor.close()
    connection.close()
    
    # Converte objetos time para string
    formularios_serializaveis = []
    for formulario in formularios:
        formulario_dict = dict(formulario)
        # Converte time para string se existir
        if formulario_dict.get('hora_inicio'):
            formulario_dict['hora_inicio'] = str(formulario_dict['hora_inicio'])
        if formulario_dict.get('hora_saida'):
            formulario_dict['hora_saida'] = str(formulario_dict['hora_saida'])
        formularios_serializaveis.append(formulario_dict)
    
    return jsonify(formularios_serializaveis)

@formularios_bp.route('/<int:id_formulario>', methods=['GET'])
def obter_formulario(id_formulario):
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT f.*, ag.matricula AS agente_matricula
        FROM formularioporcasa f
        JOIN agente ag ON f.idagente = ag.idagente
        WHERE f.idboletimdiario = %s;
    """, (id_formulario,))
    formulario = cursor.fetchone()
    cursor.close()
    connection.close()
    if formulario:
        # Converte time para string
        formulario_dict = dict(formulario)
        if formulario_dict.get('hora_inicio'):
            formulario_dict['hora_inicio'] = str(formulario_dict['hora_inicio'])
        if formulario_dict.get('hora_saida'):
            formulario_dict['hora_saida'] = str(formulario_dict['hora_saida'])
        return jsonify(formulario_dict)
    return jsonify({"erro": "Formulário não encontrado"}), 404

@formularios_bp.route('/', methods=['POST'])
def criar_formulario():
    dados = request.get_json()
    connection = get_connection()
    cursor = connection.cursor()
    
    try:
        # Processar timestamps automáticos do frontend
        timestamp_inicio = dados.get('timestamp_inicio')
        timestamp_fim = dados.get('timestamp_fim')
        
        # Extrair apenas a hora dos timestamps (HH:MM)
        hora_inicio = None
        hora_saida = None
        
        if timestamp_inicio:
            try:
                # Converte timestamp para objeto datetime e extrai hora
                dt_inicio = datetime.fromisoformat(timestamp_inicio.replace('Z', '+00:00'))
                hora_inicio = dt_inicio.strftime('%H:%M')
            except:
                hora_inicio = dados.get('hora_inicio')
        
        if timestamp_fim:
            try:
                dt_fim = datetime.fromisoformat(timestamp_fim.replace('Z', '+00:00'))
                hora_saida = dt_fim.strftime('%H:%M')
            except:
                hora_saida = dados.get('hora_saida')
        
        # Usar horários fornecidos se os timestamps não estiverem disponíveis
        if not hora_inicio:
            hora_inicio = dados.get('hora_inicio')
        if not hora_saida:
            hora_saida = dados.get('hora_saida')

        # 1. Insere o formulário com timestamps
        cursor.execute("""
            INSERT INTO formularioporcasa (
                data, bairro, endereco, tipo_inseto, hora_inicio, hora_saida,
                num_pontos_criticos, total_criaduros_encontrados, criaduros_eliminados, tipos_criaduros,
                num_locos_larva, num_locos_positivos, num_adultos_encontrados,
                num_adultos_coletados, acaorealizada, inseticida_usado,
                quantidade_inseticida, casos_suspeitos, nome_pessoa,
                telefone_pessoa, observacoes, idagente,
                timestamp_inicio, timestamp_fim, geolocalizacao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING idboletimdiario;
        """, (
            dados['data'], dados['bairro'], dados['endereco'], dados['tipo_inseto'],
            hora_inicio, hora_saida,
            dados['num_pontos_criticos'], dados['total_criaduros_encontrados'], 
            dados['criaduros_eliminados'], dados['tipos_criaduros'],
            dados['num_locos_larva'], dados['num_locos_positivos'], 
            dados['num_adultos_encontrados'], dados['num_adultos_coletados'],
            dados['acaorealizada'], dados['inseticida_usado'],
            dados['quantidade_inseticida'], dados['casos_suspeitos'], 
            dados['nome_pessoa'], dados['telefone_pessoa'], 
            dados['observacoes'], dados['idagente'],
            timestamp_inicio,  # Timestamp completo ISO
            timestamp_fim,     # Timestamp completo ISO
            dados.get('geolocalizacao')  # { "lat": -23.5, "lng": -46.6 }
        ))
        novo_id = cursor.fetchone()[0]
        
        # 2. ATUALIZA AUTOMATICAMENTE O RESUMO DIÁRIO
        cursor.execute("""
            -- Primeiro deleta se já existir resumo para essa data e agente
            DELETE FROM resumodiario 
            WHERE data = %s AND idagente = %s;
            
            -- Depois insere o novo resumo
            INSERT INTO resumodiario (
                data, idagente, total_domicilios_visitados, total_pontos_criticos,
                total_criaduros_encontrados, total_criaduros_eliminados,
                total_larvas_encontradas, total_larvas_coletadas,
                total_adultos_coletados, total_casos_suspeitos
            )
            SELECT 
                data, idagente, COUNT(*) as total_domicilios_visitados,
                SUM(num_pontos_criticos) as total_pontos_criticos,
                SUM(total_criaduros_encontrados) as total_criaduros_encontrados,
                SUM(criaduros_eliminados) as total_criaduros_eliminados,
                SUM(num_locos_larva) as total_larvas_encontradas,
                SUM(num_locos_positivos) as total_larvas_coletadas,
                SUM(num_adultos_coletados) as total_adultos_coletados,
                SUM(casos_suspeitos) as total_casos_suspeitos
            FROM formularioporcasa 
            WHERE data = %s AND idagente = %s
            GROUP BY data, idagente;
        """, (dados['data'], dados['idagente'], dados['data'], dados['idagente']))
        
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({
            "mensagem": "Formulário criado com sucesso", 
            "id_formulario": novo_id,
            "resumo_atualizado": True,
            "timestamps_capturados": bool(timestamp_inicio and timestamp_fim)
        }), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao criar formulário: {str(e)}"}), 500

@formularios_bp.route('/resumo/diario', methods=['GET'])
def resumo_diario():
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
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
    cursor.close()
    connection.close()
    return jsonify(resumo)

@formularios_bp.route('/gerar-resumo-diario/<data>', methods=['POST'])
def gerar_resumo_diario(data):
    """Gera/atualiza resumo diário para uma data específica"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            -- Primeiro deleta resumos existentes para essa data
            DELETE FROM resumodiario WHERE data = %s;
            
            -- Depois insere os novos resumos
            INSERT INTO resumodiario (
                data, idagente, total_domicilios_visitados, total_pontos_criticos,
                total_criaduros_encontrados, total_criaduros_eliminados,
                total_larvas_encontradas, total_larvas_coletadas,
                total_adultos_coletados, total_casos_suspeitos
            )
            SELECT 
                data, idagente, COUNT(*) as total_domicilios_visitados,
                SUM(num_pontos_criticos) as total_pontos_criticos,
                SUM(total_criaduros_encontrados) as total_criaduros_encontrados,
                SUM(criaduros_eliminados) as total_criaduros_eliminados,
                SUM(num_locos_larva) as total_larvas_encontradas,
                SUM(num_locos_positivos) as total_larvas_coletadas,
                SUM(num_adultos_coletados) as total_adultos_coletados,
                SUM(casos_suspeitos) as total_casos_suspeitos
            FROM formularioporcasa 
            WHERE data = %s
            GROUP BY data, idagente;
        """, (data, data))
        
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"mensagem": f"Resumo diário gerado/atualizado para {data}"}), 201
        
    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return jsonify({"erro": f"Erro ao gerar resumo: {str(e)}"}), 500