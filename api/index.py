from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "¡Flask funcionando en Vercel!", 
        "status": "success"
    })

@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({"data": "Test exitoso"})

# MANEJADOR de errores 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint no encontrado",
        "code": 404,
        "message": "La ruta solicitada no existe"
    }), 404

# CONFIGURACIÓN CRÍTICA para Vercel
if __name__ == '__main__':
    app.run(debug=True)
else:
    # Esto es ESSENTIAL para serverless functions
    application = app