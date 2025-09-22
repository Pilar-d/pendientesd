# api/index.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Vercel Flask!'

# Esto es crucial para Vercel
if __name__ == '__main__':
    app.run()
else:
    application = app