from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Funcionando en Vercel"})

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy"})

# IMPORTANTE: Para Vercel Functions
if __name__ == '__main__':
    app.run(debug=True)
else:
    # Para entornos serverless
    import os
    if os.environ.get('VERCEL'):
        # Exporta la app para Vercel
        application = app