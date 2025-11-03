from flask import Flask, request
from flask_cors import CORS
from routes.usuarios import usuarios_bp
from routes.formularios import formularios_bp
from routes.resumos import resumos_bp

app = Flask(__name__)

# Evita redirects automáticos por trailing slash (/rota -> /rota/)
app.url_map.strict_slashes = False

# Configura CORS explicitamente (permitir seu frontend)
CORS(
    app,
    origins=["http://localhost:5173"],           # adicione outros origins se necessário
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

# Opcional: responder rapidamente a OPTIONS antes de qualquer outro middleware
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return ("", 200)

app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
app.register_blueprint(formularios_bp, url_prefix="/formularios")
app.register_blueprint(resumos_bp, url_prefix="/resumos")

@app.route("/")
def home():
    return {"mensagem": "API EntomoTrack conectada ao PostgreSQL!"}

if __name__ == "__main__":
    app.run(debug=True)