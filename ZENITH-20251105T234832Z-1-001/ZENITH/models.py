# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    """Modelo para la tabla de Usuarios."""
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    fecha_registro = db.Column(db.Date, default=datetime.utcnow)
    
    # NUEVO CAMPO PARA PERMISOS DE ADMIN
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relaciones actualizadas según el documento
    consumos = db.relationship('Consumo', backref='usuario', lazy=True, cascade="all, delete-orphan")
    consumos_anuales = db.relationship('Consumo_Anual_Historico', backref='usuario', lazy=True, cascade="all, delete-orphan")
    alertas = db.relationship('Alerta', backref='usuario', lazy=True, cascade="all, delete-orphan") 
    facturas = db.relationship('Factura', backref='usuario', lazy=True, cascade="all, delete-orphan") 
    ahorros = db.relationship('Ahorro', backref='usuario', lazy=True, cascade="all, delete-orphan") 
    evaluaciones = db.relationship('Evaluacion', backref='usuario', lazy=True, cascade="all, delete-orphan") 

    def __repr__(self):
        return f"Usuario('{self.nombre_usuario}', '{self.email}')"

class Tipo_Servicio(db.Model):
    """Modelo para la tabla de Tipos de Servicio (Electricidad, Agua, Gas, Internet)."""
    id_tipo_servicio = db.Column(db.Integer, primary_key=True)
    nombre_servicio = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relaciones
    consumos = db.relationship('Consumo', backref='tipo_servicio', lazy=True)
    alertas = db.relationship('Alerta', backref='tipo_servicio', lazy=True)
    plantillas_alerta = db.relationship('Plantilla_Alerta', backref='tipo_servicio', lazy=True) 

    def __repr__(self):
        return f"Tipo_Servicio('{self.nombre_servicio}')"

class Consumo(db.Model):
    """Modelo para registrar el consumo histórico mensual (registros individuales)."""
    id_consumo = db.Column(db.Integer, primary_key=True)
    valor_consumo = db.Column(db.Float, nullable=False)
    fecha_consumo = db.Column(db.Date, nullable=False)
    costo_total = db.Column(db.Float, nullable=True) 
    
    # Claves Foráneas
    fk_id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    fk_id_tipo_servicio = db.Column(db.Integer, db.ForeignKey('tipo__servicio.id_tipo_servicio'), nullable=False)

    def __repr__(self):
        return f"Consumo('{self.valor_consumo}', '{self.fecha_consumo}')"

# --- TABLA RENOMBRADA: PLANTILLAS DE ALERTAS ---
class Plantilla_Alerta(db.Model):
    """Almacena los mensajes prefabricados para las alertas de alto consumo."""
    __tablename__ = 'plantilla_alerta'
    id_plantilla = db.Column(db.Integer, primary_key=True)
    fk_id_tipo_servicio = db.Column(db.Integer, db.ForeignKey('tipo__servicio.id_tipo_servicio'), nullable=False)
    plantilla_mensaje = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f"Plantilla_Alerta('{self.tipo_servicio.nombre_servicio}')"


class Consumo_Anual_Historico(db.Model):
    """Modelo para guardar el resumen de consumo anual por usuario."""
    id_historial = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False)
    total_consumo_electricidad = db.Column(db.Float, default=0.0)
    total_consumo_agua = db.Column(db.Float, default=0.0)
    total_consumo_gas = db.Column(db.Float, default=0.0)
    total_consumo_internet = db.Column(db.Float, default=0.0)
    fk_id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)

    def __repr__(self):
        return f"Consumo_Anual_Historico(Usuario: {self.fk_id_usuario}, Año: {self.anio})"

# --- TABLA RENOMBRADA: MODELO DE ALERTAS (Basado en Tabla 16) ---
class Alerta(db.Model):
    """Modelo para alertas y recomendaciones (Tabla 16)."""
    __tablename__ = 'alerta'
    id_alerta = db.Column(db.Integer, primary_key=True)
    texto_alerta = db.Column(db.String(500), nullable=False) 
    fecha_creacion = db.Column(db.Date, default=datetime.utcnow) 
    
    # Claves Foráneas
    fk_id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    fk_id_tipo_servicio = db.Column(db.Integer, db.ForeignKey('tipo__servicio.id_tipo_servicio'), nullable=True) 

    def __repr__(self):
        return f"Alerta('{self.texto_alerta[:20]}...')"

# --- NUEVA TABLA: FACTURA (Basado en Tabla 14) ---
class Factura(db.Model):
    """Modelo para registrar facturas y archivos (Tabla 14)."""
    __tablename__ = 'factura'
    id_factura = db.Column(db.Integer, primary_key=True)
    periodo = db.Column(db.String(7), nullable=False) 
    monto_total = db.Column(db.Float, nullable=False)
    archivo_uri = db.Column(db.String(255), nullable=True) 
    fecha_generada = db.Column(db.Date, default=datetime.utcnow)
    
    # Clave Foránea
    fk_id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)

    def __repr__(self):
        return f"Factura(Usuario: {self.fk_id_usuario}, Periodo: {self.periodo})"

# --- NUEVA TABLA: AHORRO (Basado en Tabla 17) ---
class Ahorro(db.Model):
    """Modelo para registrar el ahorro obtenido (Tabla 17)."""
    __tablename__ = 'ahorro'
    id_ahorro = db.Column(db.Integer, primary_key=True)
    periodo = db.Column(db.String(7), nullable=False) 
    ahorro_economico_total = db.Column(db.Float, default=0.0) 
    
    # Clave Foránea
    fk_id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)

    def __repr__(self):
        return f"Ahorro(Usuario: {self.fk_id_usuario}, Periodo: {self.periodo})"

# --- NUEVA TABLA: EVALUACION (Basado en Tabla 19) ---
class Evaluacion(db.Model):
    """Modelo para la evaluación de la app por usuarios (Tabla 19)."""
    __tablename__ = 'evaluacion'
    id_evaluacion = db.Column(db.Integer, primary_key=True)
    calificacion = db.Column(db.Integer, nullable=False) # 1-5
    comentario = db.Column(db.String(500), nullable=True)
    fecha_evaluacion = db.Column(db.Date, default=datetime.utcnow)

    # Clave Foránea
    fk_id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)

    def __repr__(self):
        return f"Evaluacion(Usuario: {self.fk_id_usuario}, Calificacion: {self.calificacion})"