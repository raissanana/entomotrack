from flask import Flask
from routes.usuarios import usuarios_bp
from routes.formularios import formularios_bp
from routes.resumos import resumos_bp

app = Flask(__name__)

app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
app.register_blueprint(formularios_bp, url_prefix='/formularios')
app.register_blueprint(resumos_bp, url_prefix='/resumos')

@app.route('/')
def home():
    return {'mensagem': 'API EntomoTrack conectada ao PostgreSQL!'}

if __name__ == '__main__':
    app.run(debug=True)