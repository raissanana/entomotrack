from flask import Flask
from routes.usuarios import usuarios_bp
from routes.boletins import boletins_bp

app = Flask(__name__)

app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
app.register_blueprint(boletins_bp, url_prefix='/boletins')

@app.route('/')
def home():
    return {'mensagem': 'API EntomoTrack conectada ao MySQL!'}

if __name__ == '__main__':
    app.run(debug=True)
