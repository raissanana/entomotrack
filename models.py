class Usuario:
    def __init__(self, id_usuario, nome, email, senha, funcao, telefone):
        self.id_usuario = id_usuario
        self.nome = nome
        self.email = email
        self.senha = senha
        self.funcao = funcao
        self.telefone = telefone

class AgenteEndemias:
    def __init__(self, id_agente, id_usuario, matricula):
        self.id_agente = id_agente
        self.id_usuario = id_usuario
        self.matricula = matricula

class Bairro:
    def __init__(self, id_bairro, nome):
        self.id_bairro = id_bairro
        self.nome = nome

class BoletimDiario:
    def __init__(self, id_boletim, id_agente, id_bairro, data, total_casos, observacoes):
        self.id_boletim = id_boletim
        self.id_agente = id_agente
        self.id_bairro = id_bairro
        self.data = data
        self.total_casos = total_casos
        self.observacoes = observacoes