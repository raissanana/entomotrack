from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.usuarios import usuarios_bp
from routes.formularios import formularios_bp
from routes.resumos import resumos_bp
from database import get_connection

app = Flask(__name__)

# Evita redirects automáticos por trailing slash (/rota -> /rota/)
app.url_map.strict_slashes = False

# Configura CORS explicitamente (permitir seu frontend)
CORS(
    app,
    origins=["http://localhost:5173", os.environ.get("FRONTEND_URL", "https://entomo-track-frontend.vercel.app")],  # ajuste se precisar de mais origins
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)

# Opcional: responder rapidamente a OPTIONS antes de qualquer outro middleware
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return ("", 200)

# Health-check rápido
@app.route("/health", methods=["GET"])
def health():
    conn = get_connection()
    if conn is None:
        return jsonify({"healthy": False, "db": False}), 500
    try:
        conn.close()
        return jsonify({"healthy": True, "db": True}), 200
    except Exception:
        return jsonify({"healthy": True, "db": False}), 500

app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
app.register_blueprint(formularios_bp, url_prefix="/formularios")
app.register_blueprint(resumos_bp, url_prefix="/resumos")

@app.route("/")
def home():
    return {"mensagem": "API EntomoTrack conectada ao PostgreSQL!"}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
