from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_staff = db.Column(db.Boolean, default=False)
    is_superuser = db.Column(db.Boolean, default=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con las tareas
    tareas = db.relationship('Tarea', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def get_id(self):
        """Método requerido por Flask-Login"""
        return str(self.id)
    
    def set_password(self, password):
        """Establecer la contraseña hasheada"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar la contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def has_perm(self, perm, obj=None):
        """Verificar permisos (compatibilidad con Django)"""
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        """Verificar permisos de módulo (compatibilidad con Django)"""
        return self.is_superuser
    
    def __str__(self):
        return self.username
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class Tarea(db.Model):
    __tablename__ = 'tarea'
    
    # Opciones para categorías
    CATEGORIA_LABORAL = 'laboral'
    CATEGORIA_PERSONAL = 'personal'
    CATEGORIA_ESTUDIO = 'estudio'
    CATEGORIA_HOGAR = 'hogar'
    CATEGORIA_OTROS = 'otros'
    
    CATEGORIA_CHOICES = [
        (CATEGORIA_LABORAL, 'Laboral'),
        (CATEGORIA_PERSONAL, 'Personal'),
        (CATEGORIA_ESTUDIO, 'Estudio'),
        (CATEGORIA_HOGAR, 'Hogar'),
        (CATEGORIA_OTROS, 'Otros'),
    ]
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    completada = db.Column(db.Boolean, default=False)
    creada_en = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_limite = db.Column(db.Date, nullable=True)
    categoria = db.Column(db.String(20), default=CATEGORIA_LABORAL)
    
    # Clave foránea para el usuario
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    @property
    def categoria_display(self):
        """Obtener el nombre legible de la categoría"""
        dict_categorias = dict(self.CATEGORIA_CHOICES)
        return dict_categorias.get(self.categoria, self.categoria)
    
    @property
    def esta_vencida(self):
        """Verificar si la tarea está vencida"""
        if self.fecha_limite:
            return not self.completada and self.fecha_limite < datetime.now().date()
        return False
    
    @property
    def dias_restantes(self):
        """Calcular días restantes para la fecha límite"""
        if self.fecha_limite:
            hoy = datetime.now().date()
            diferencia = (self.fecha_limite - hoy).days
            return diferencia
        return None
    
    def __str__(self):
        return f'Tarea: {self.titulo}'
    
    def __repr__(self):
        return f'<Tarea {self.titulo}>'