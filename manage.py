import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from models import db, Usuario, Tarea
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import sqlite3
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, template_folder='Home/templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-temporal-desarrollo')

# Configuración mejorada para Vercel y base de datos
if os.environ.get('VERCEL'):
    # Configuración para Vercel - usar PostgreSQL si está disponible
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Asegurar formato correcto para PostgreSQL
        if database_url.startswith('postgres://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://')
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # SQLite en /tmp para Vercel (datos temporales)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/tareas.db'
else:
    # Configuración para desarrollo local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tareas.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Crear tablas de base de datos (solo si no existen)
with app.app_context():
    try:
        # Verificar si las tablas existen
        db.session.execute(text("SELECT 1 FROM usuario LIMIT 1")).fetchall()
        db.session.execute(text("SELECT 1 FROM tarea LIMIT 1")).fetchall()
        print("La base de datos ya tiene las tablas necesarias")
        
        # Verificar si existen las columnas específicas
        try:
            db.session.execute(text("SELECT fecha_limite, categoria FROM tarea LIMIT 1")).fetchall()
            print("Las columnas específicas ya existen")
        except OperationalError:
            print("Faltan algunas columnas, recreando tablas...")
            db.drop_all()
            db.create_all()
            print("Tablas recreadas correctamente")
            
    except OperationalError:
        print("La base de datos necesita creación. Creando tablas...")
        try:
            db.drop_all()
            db.create_all()
            
            # Crear un usuario de ejemplo si estamos en desarrollo
            if not os.environ.get('VERCEL'):
                usuario_ejemplo = Usuario(username='admin')
                usuario_ejemplo.set_password('admin123')
                db.session.add(usuario_ejemplo)
                db.session.commit()
                print("Usuario de ejemplo creado: admin/admin123")
            
            print("Tablas creadas correctamente")
        except Exception as e:
            print(f"Error al crear tablas: {str(e)}")

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and usuario.check_password(password):
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if Usuario.query.filter_by(username=username).first():
            flash('El usuario ya existe', 'error')
            return redirect(url_for('register'))
        
        nuevo_usuario = Usuario(username=username)
        nuevo_usuario.set_password(password)
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

# Rutas de tareas
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Obtener parámetros de búsqueda y ordenamiento
    q = request.args.get('q', '')
    orden = request.args.get('orden', 'recientes')
    filtro_categoria = request.args.get('categoria', '')
    
    # Consulta base con manejo de errores
    try:
        consulta = Tarea.query.filter_by(usuario_id=session['user_id'])
        
        # Aplicar búsqueda
        if q:
            consulta = consulta.filter(
                (Tarea.titulo.ilike(f'%{q}%')) | (Tarea.descripcion.ilike(f'%{q}%'))
            )
        
        # Aplicar filtro por categoría
        if filtro_categoria:
            consulta = consulta.filter(Tarea.categoria == filtro_categoria)
        
        # Aplicar ordenamiento
        if orden == 'recientes':
            consulta = consulta.order_by(Tarea.creada_en.desc())
        elif orden == 'antiguas':
            consulta = consulta.order_by(Tarea.creada_en.asc())
        elif orden == 'titulo':
            consulta = consulta.order_by(Tarea.titulo.asc())
        elif orden == 'fecha_limite':
            consulta = consulta.order_by(Tarea.fecha_limite.asc())
        
        tareas = consulta.all()
        
    except OperationalError as e:
        # Si hay error, probablemente falten columnas en la base de datos
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        tareas = []
        # Intentar recrear la base de datos
        try:
            with app.app_context():
                db.drop_all()
                db.create_all()
                flash('Base de datos reinicializada. Por favor, regístrate nuevamente.', 'info')
        except Exception as e:
            flash(f'Error crítico: {str(e)}', 'error')
    
    # Pasar la fecha actual para comparaciones
    hoy = datetime.now().date()
    
    # Obtener estadísticas
    total_tareas = len(tareas)
    tareas_completadas = sum(1 for tarea in tareas if tarea.completada)
    tareas_pendientes = total_tareas - tareas_completadas
    tareas_vencidas = sum(1 for tarea in tareas if not tarea.completada and tarea.fecha_limite and tarea.fecha_limite < hoy)
    
    return render_template('index.html', 
                         tareas=tareas, 
                         username=session['username'],
                         q=q,
                         orden=orden,
                         filtro_categoria=filtro_categoria,
                         hoy=hoy,
                         total_tareas=total_tareas,
                         tareas_completadas=tareas_completadas,
                         tareas_pendientes=tareas_pendientes,
                         tareas_vencidas=tareas_vencidas,
                         categorias=Tarea.CATEGORIA_CHOICES)

@app.route('/crear', methods=['GET', 'POST'])
def crear():
    if 'user_id' not in session:
        flash('Debes iniciar sesión primero', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        # Mostrar formulario de creación
        return render_template('crear.html', categorias=Tarea.CATEGORIA_CHOICES)
    
    try:
        titulo = request.form['titulo']
        descripcion = request.form.get('descripcion', '')
        fecha_limite_str = request.form.get('fecha_limite', '')
        categoria = request.form.get('categoria', 'laboral')
        
        # Validar título
        if not titulo.strip():
            flash('El título es obligatorio', 'error')
            return render_template('crear.html', categorias=Tarea.CATEGORIA_CHOICES)
        
        nueva_tarea = Tarea(
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            categoria=categoria,
            usuario_id=session['user_id']
        )
        
        # Convertir la fecha de string a objeto date si se proporciona
        if fecha_limite_str:
            try:
                fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
                nueva_tarea.fecha_limite = fecha_limite
            except ValueError:
                flash('Formato de fecha incorrecto', 'error')
                return render_template('crear.html', categorias=Tarea.CATEGORIA_CHOICES)
        
        db.session.add(nueva_tarea)
        db.session.commit()
        
        flash('Tarea creada exitosamente', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear la tarea: {str(e)}', 'error')
        return render_template('crear.html', categorias=Tarea.CATEGORIA_CHOICES)

@app.route('/editar/<int:tarea_id>', methods=['GET', 'POST'])
def editar(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        
        # Verificar que la tarea pertenece al usuario actual
        if tarea.usuario_id != session['user_id']:
            flash('No tienes permisos para editar esta tarea', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            titulo = request.form['titulo']
            descripcion = request.form.get('descripcion', '')
            fecha_limite_str = request.form.get('fecha_limite', '')
            categoria = request.form.get('categoria', 'laboral')
            
            # Validar título
            if not titulo.strip():
                flash('El título es obligatorio', 'error')
                return render_template('editar.html', tarea=tarea, categorias=Tarea.CATEGORIA_CHOICES)
            
            tarea.titulo = titulo.strip()
            tarea.descripcion = descripcion.strip()
            tarea.categoria = categoria
            
            # Actualizar fecha límite
            if fecha_limite_str:
                try:
                    tarea.fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato de fecha incorrecto', 'error')
                    return render_template('editar.html', tarea=tarea, categorias=Tarea.CATEGORIA_CHOICES)
            else:
                tarea.fecha_limite = None
            
            db.session.commit()
            flash('Tarea actualizada exitosamente', 'success')
            return redirect(url_for('index'))
        
        return render_template('editar.html', tarea=tarea, categorias=Tarea.CATEGORIA_CHOICES)
    
    except OperationalError as e:
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('index'))

@app.route('/toggle/<int:tarea_id>', methods=['POST'])
def toggle(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        
        # Verificar que la tarea pertenece al usuario actual
        if tarea.usuario_id != session['user_id']:
            flash('No tienes permisos para modificar esta tarea', 'error')
            return redirect(url_for('index'))
        
        tarea.completada = not tarea.completada
        db.session.commit()
        
        flash(f'Tarea marcada como {"completada" if tarea.completada else "pendiente"}', 'success')
        return redirect(url_for('index'))
    
    except OperationalError as e:
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('index'))

@app.route('/eliminar/<int:tarea_id>', methods=['POST'])
def eliminar(tarea_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        
        # Verificar que la tarea pertenece al usuario actual
        if tarea.usuario_id != session['user_id']:
            flash('No tienes permisos para eliminar esta tarea', 'error')
            return redirect(url_for('index'))
        
        db.session.delete(tarea)
        db.session.commit()
        flash('Tarea eliminada exitosamente', 'success')
        
        return redirect(url_for('index'))
    
    except OperationalError as e:
        flash('Error en la base de datos. Por favor, contacta al administrador.', 'error')
        return redirect(url_for('index'))

# Ruta para forzar la actualización de la base de datos
@app.route('/actualizar-db')
def actualizar_db():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            flash('Base de datos actualizada correctamente. Por favor, regístrate nuevamente.', 'success')
            session.clear()
        return redirect(url_for('register'))
    except Exception as e:
        flash(f'Error al actualizar la base de datos: {str(e)}', 'error')
        return redirect(url_for('index'))

# Manejo de errores
@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_servidor(error):
    return render_template('500.html'), 500

# Configuración para Vercel
if __name__ == '__main__':
    app.run(debug=True)
else:
    # Esta línea es crucial para que Vercel pueda ejecutar la aplicación
    application = app