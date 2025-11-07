from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract, and_
import os
from functools import wraps 
import random

from models import db, Usuario, Consumo, Tipo_Servicio, Alerta, Consumo_Anual_Historico, Plantilla_Alerta, Factura, Ahorro, Evaluacion

app = Flask(__name__)
app.config['SECRET_KEY'] = 'una_clave_secreta_muy_larga_y_segura_para_zenith'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ZENITH.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads', 'facturas')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

UMBRAL_ALERTA = 1.2

def generar_alerta_si_es_necesario(usuario_id, consumo_obj, tipo_servicio):
    
    consumo_actual = consumo_obj.valor_consumo
    
    promedio_historico = db.session.query(
        func.avg(Consumo.valor_consumo)
    ).filter(
        Consumo.fk_id_usuario == usuario_id,
        Consumo.fk_id_tipo_servicio == tipo_servicio.id_tipo_servicio,
        Consumo.id_consumo != consumo_obj.id_consumo
    ).scalar() or 0.0

    if promedio_historico > 0 and consumo_actual > promedio_historico * UMBRAL_ALERTA:
        porcentaje_exceso = ((consumo_actual / promedio_historico) - 1) * 100
        
        mensaje_plantilla_obj = Plantilla_Alerta.query.filter_by(
            fk_id_tipo_servicio=tipo_servicio.id_tipo_servicio
        ).first()
        
        if mensaje_plantilla_obj:
            texto_alerta = mensaje_plantilla_obj.plantilla_mensaje.format(
                consumo_actual=consumo_actual,
                promedio_historico=promedio_historico,
                porcentaje_exceso=porcentaje_exceso
            )
        else:
            texto_alerta = (
                f"⚠️ ¡Pico de Consumo en {tipo_servicio.nombre_servicio}! "
                f"Tu registro de {consumo_actual:.2f} ha excedido el promedio mensual ({promedio_historico:.2f}) "
                f"en un {porcentaje_exceso:.0f}%."
            )
        
        nueva_alerta = Alerta(
            texto_alerta=texto_alerta,
            fk_id_usuario=usuario_id,
            fk_id_tipo_servicio=tipo_servicio.id_tipo_servicio,
            fecha_creacion=date.today()
        )
        db.session.add(nueva_alerta)

def actualizar_historial_anual(usuario_id, nuevo_registro, tipo_servicio_nombre):
    anio_registro = nuevo_registro.fecha_consumo.year
    
    historial = Consumo_Anual_Historico.query.filter(
        Consumo_Anual_Historico.fk_id_usuario == usuario_id,
        Consumo_Anual_Historico.anio == anio_registro
    ).first()

    if not historial:
        historial = Consumo_Anual_Historico(fk_id_usuario=usuario_id, anio=anio_registro)
        db.session.add(historial)
    
    if tipo_servicio_nombre == 'Electricidad':
        historial.total_consumo_electricidad = (historial.total_consumo_electricidad or 0.0) + nuevo_registro.valor_consumo
    elif tipo_servicio_nombre == 'Agua':
        historial.total_consumo_agua = (historial.total_consumo_agua or 0.0) + nuevo_registro.valor_consumo
    elif tipo_servicio_nombre == 'Gas':
        historial.total_consumo_gas = (historial.total_consumo_gas or 0.0) + nuevo_registro.valor_consumo
    elif tipo_servicio_nombre == 'Internet':
        historial.total_consumo_internet = (historial.total_consumo_internet or 0.0) + nuevo_registro.valor_consumo
        
def actualizar_ahorro_mensual(usuario_id, fecha_consumo, consumo_actual_obj):
    if consumo_actual_obj.costo_total is None:
        return 

    periodo_actual_str = fecha_consumo.strftime('%Y-%m')
    
    fecha_mes_anterior = (fecha_consumo.replace(day=1) - timedelta(days=1))
    
    
    costo_total_mes_anterior_todos = db.session.query(
        func.sum(Consumo.costo_total)
    ).filter(
        Consumo.fk_id_usuario == usuario_id,
        extract('year', Consumo.fecha_consumo) == fecha_mes_anterior.year,
        extract('month', Consumo.fecha_consumo) == fecha_mes_anterior.month
    ).scalar() or 0.0
    
    costo_total_mes_actual_todos = db.session.query(
        func.sum(Consumo.costo_total)
    ).filter(
        Consumo.fk_id_usuario == usuario_id,
        extract('year', Consumo.fecha_consumo) == fecha_consumo.year,
        extract('month', Consumo.fecha_consumo) == fecha_consumo.month
    ).scalar() or 0.0
    
    registro_ahorro = Ahorro.query.filter_by(
        fk_id_usuario=usuario_id,
        periodo=periodo_actual_str
    ).first()
    
    if not registro_ahorro:
        registro_ahorro = Ahorro(
            fk_id_usuario=usuario_id,
            periodo=periodo_actual_str,
            ahorro_economico_total=0.0
        )
        db.session.add(registro_ahorro)
    
    if costo_total_mes_anterior_todos > 0:
         registro_ahorro.ahorro_economico_total = costo_total_mes_anterior_todos - costo_total_mes_actual_todos
    else:
         registro_ahorro.ahorro_economico_total = 0.0 

def get_date_for_month(i):
    hoy = date.today()
    mes_iter = hoy.month - (11 - i)
    anio_iter = hoy.year
    if mes_iter <= 0:
        mes_iter += 12
        anio_iter -= 1
    return date(anio_iter, mes_iter, 15)

def inicializar_db_con_datos_basicos():
    db.create_all()

    if Tipo_Servicio.query.count() == 0:
        servicios_basicos = ['Electricidad', 'Agua', 'Gas', 'Internet']
        for nombre in servicios_basicos:
            servicio = Tipo_Servicio(nombre_servicio=nombre)
            db.session.add(servicio)
        db.session.commit()
        print("✅ Tipos de Servicio insertados.")

    if Plantilla_Alerta.query.count() == 0:
        servicios = {s.nombre_servicio: s.id_tipo_servicio for s in Tipo_Servicio.query.all()}
        if 'Electricidad' in servicios:
            mensajes = [
                (servicios['Electricidad'], "⚠️ ¡Pico de Consumo en Electricidad! Tu registro de {consumo_actual:.2f} kWh ha excedido el promedio mensual ({promedio_historico:.2f} kWh) en un {porcentaje_exceso:.0f}%. Revisa tus electrodomésticos."),
                (servicios['Agua'], "💧 ¡Pico de Consumo en Agua! Tu registro de {consumo_actual:.2f} m³ ha excedido el promedio mensual ({promedio_historico:.2f} m³) en un {porcentaje_exceso:.0f}%. ¡Revisa si hay fugas!"),
                (servicios['Gas'], "🔥 ¡Pico de Consumo en Gas! Tu registro de {consumo_actual:.2f} m³ ha excedido el promedio mensual ({promedio_historico:.2f} m³) en un {porcentaje_exceso:.0f}%. Revisa el calentador."),
                (servicios['Internet'], "💻 ¡Pico de Consumo en Internet! Tu registro de {consumo_actual:.2f} GB ha excedido el promedio mensual ({promedio_historico:.2f} GB) en un {porcentaje_exceso:.0f}%.")
            ]
            for fk_servicio, plantilla in mensajes:
                mensaje = Plantilla_Alerta(fk_id_tipo_servicio=fk_servicio, plantilla_mensaje=plantilla)
                db.session.add(mensaje)
            db.session.commit()
            print("✅ Plantillas de Alerta prefabricadas insertadas.")
        else:
            print("⚠️ No se pudieron insertar plantillas de alerta, tipos de servicio no encontrados.")
            
    if Usuario.query.filter_by(email='admin@zenith.com').first() is None:
        admin_user = Usuario(
            nombre_usuario='Administrador',
            email='admin@zenith.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin_user)
        print("✅ Usuario Administrador ('admin@zenith.com' / 'admin123') Creado.")

    if Usuario.query.filter_by(email='miguel@zenith.com').first() is None:
        miguel_user = Usuario(
            nombre_usuario='Miguel Espinel León',
            email='miguel@zenith.com',
            password_hash=generate_password_hash('miguel123'),
            is_admin=False
        )
        db.session.add(miguel_user)
        print("✅ Usuario de prueba (Miguel) Creado.")

    if Usuario.query.filter_by(email='akira@zenith.com').first() is None:
        akira_user = Usuario(
            nombre_usuario='Akira Kawakami Peña',
            email='akira@zenith.com',
            password_hash=generate_password_hash('akira123'),
            is_admin=False
        )
        db.session.add(akira_user)
        print("✅ Usuario de prueba (Akira) Creado.")

    if Usuario.query.filter_by(email='juan@zenith.com').first() is None:
        juan_user = Usuario(
            nombre_usuario='Juan Carlos Rojas Muñoz',
            email='juan@zenith.com',
            password_hash=generate_password_hash('juan123'),
            is_admin=False
        )
        db.session.add(juan_user)
        print("✅ Usuario de prueba (Juan) Creado.")

    db.session.commit()

    if Consumo.query.count() == 0:
        print("Iniciando carga de datos de prueba de 1 año (solo enteros)...")
        
        u_miguel = Usuario.query.filter_by(email='miguel@zenith.com').first()
        u_akira = Usuario.query.filter_by(email='akira@zenith.com').first()
        u_juan = Usuario.query.filter_by(email='juan@zenith.com').first()
        
        s_electricidad = Tipo_Servicio.query.filter_by(nombre_servicio='Electricidad').first()
        s_agua = Tipo_Servicio.query.filter_by(nombre_servicio='Agua').first()
        s_gas = Tipo_Servicio.query.filter_by(nombre_servicio='Gas').first()
        s_internet = Tipo_Servicio.query.filter_by(nombre_servicio='Internet').first()

        if not all([u_miguel, u_akira, u_juan, s_electricidad, s_agua, s_gas, s_internet]):
            print("⚠️ No se pudieron cargar datos de prueba (faltan usuarios o servicios base).")
            return

        try:
            consumos_a_registrar = []
            
            for i in range(12):
                fecha_consumo = get_date_for_month(i)
                
                if i < 11:
                    val_elec_miguel = random.randint(140, 160)
                    val_agua_miguel = random.randint(20, 24)
                    val_gas_miguel = random.randint(15, 20)
                    val_inet_miguel = random.randint(90, 110)
                else: 
                    val_elec_miguel = 300 
                    val_agua_miguel = 40
                    val_gas_miguel = 50
                    val_inet_miguel = 200
                
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_miguel.id_usuario, fk_id_tipo_servicio=s_electricidad.id_tipo_servicio, valor_consumo=val_elec_miguel, costo_total=val_elec_miguel * 500, fecha_consumo=fecha_consumo))
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_miguel.id_usuario, fk_id_tipo_servicio=s_agua.id_tipo_servicio, valor_consumo=val_agua_miguel, costo_total=val_agua_miguel * 1500, fecha_consumo=fecha_consumo))
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_miguel.id_usuario, fk_id_tipo_servicio=s_gas.id_tipo_servicio, valor_consumo=val_gas_miguel, costo_total=val_gas_miguel * 900, fecha_consumo=fecha_consumo))
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_miguel.id_usuario, fk_id_tipo_servicio=s_internet.id_tipo_servicio, valor_consumo=val_inet_miguel, costo_total=val_inet_miguel * 500, fecha_consumo=fecha_consumo))
                
                val_gas_akira = random.randint(30, 35)
                val_inet_akira = random.randint(100, 120)
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_akira.id_usuario, fk_id_tipo_servicio=s_gas.id_tipo_servicio, valor_consumo=val_gas_akira, costo_total=val_gas_akira * 900, fecha_consumo=fecha_consumo))
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_akira.id_usuario, fk_id_tipo_servicio=s_internet.id_tipo_servicio, valor_consumo=val_inet_akira, costo_total=val_inet_akira * 500, fecha_consumo=fecha_consumo))
                
                val_inet_juan = random.randint(80, 90)
                costo_inet_juan = None
                if i >= 6: 
                    costo_inet_juan = val_inet_juan * 550
                consumos_a_registrar.append(Consumo(fk_id_usuario=u_juan.id_usuario, fk_id_tipo_servicio=s_internet.id_tipo_servicio, valor_consumo=val_inet_juan, costo_total=costo_inet_juan, fecha_consumo=fecha_consumo))

            db.session.add_all(consumos_a_registrar)
            db.session.commit() 
            
            consumos_ordenados = Consumo.query.order_by(Consumo.fecha_consumo.asc()).all()
            for c in consumos_ordenados:
                servicio = Tipo_Servicio.query.get(c.fk_id_tipo_servicio)
                actualizar_historial_anual(c.fk_id_usuario, c, servicio.nombre_servicio)
                if c.costo_total is not None:
                    actualizar_ahorro_mensual(c.fk_id_usuario, c.fecha_consumo, c)

            
            
            
            usuarios = [u_miguel, u_akira, u_juan]
            servicios_todos = [s_electricidad, s_agua, s_gas, s_internet]
            for u in usuarios:
                for s in servicios_todos:
                    consumo_reciente = Consumo.query.filter(Consumo.fk_id_usuario == u.id_usuario, Consumo.fk_id_tipo_servicio == s.id_tipo_servicio).order_by(Consumo.fecha_consumo.desc()).first()
                    if consumo_reciente:
                        generar_alerta_si_es_necesario(u.id_usuario, consumo_reciente, s)
            
            db.session.add(Factura(fk_id_usuario=u_akira.id_usuario, periodo=get_date_for_month(11).strftime('%Y-%m'), monto_total=95000, fecha_generada=date.today()))
            db.session.add(Factura(fk_id_usuario=u_akira.id_usuario, periodo=get_date_for_month(10).strftime('%Y-%m'), monto_total=92000, fecha_generada=date.today()))
            db.session.add(Factura(fk_id_usuario=u_akira.id_usuario, periodo=get_date_for_month(9).strftime('%Y-%m'), monto_total=93500, fecha_generada=date.today()))
            
            db.session.commit()
            print("✅ Datos de prueba de 1 año (enteros) cargados para todos los usuarios.")
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al cargar datos de prueba: {str(e)}")


@app.route('/')
def landing():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/acceso')
def inicio():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('inicio.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('inicio'))
    if session.get('is_admin'): 
        return redirect(url_for('admin_dashboard'))

    usuario_actual = Usuario.query.get(session['user_id'])
    tipos_servicio = Tipo_Servicio.query.all()
    
    return render_template('index.html', usuario=usuario_actual, tipos_servicio=tipos_servicio)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None) 
    return redirect(url_for('landing'))

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() 
    usuario = Usuario.query.filter_by(email=data.get('email')).first()
    
    if usuario and check_password_hash(usuario.password_hash, data.get('password')):
        session['user_id'] = usuario.id_usuario 
        session['is_admin'] = usuario.is_admin 
        
        if usuario.is_admin:
            return jsonify({
                'success': True, 
                'message': 'Inicio de sesión de Admin exitoso. Redirigiendo...',
                'redirect_url': url_for('admin_dashboard') 
            })
        else:
            return jsonify({
                'success': True, 
                'message': 'Inicio de sesión exitoso',
                'redirect_url': url_for('dashboard') 
            })
    else:
        return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if Usuario.query.filter_by(email=data.get('email')).first():
        return jsonify({'success': False, 'message': 'El email ya está registrado'}), 400
    
    if data.get('email') == 'admin@zenith.com':
         return jsonify({'success': False, 'message': 'Este email está reservado.'}), 400

    nuevo_usuario = Usuario(
        nombre_usuario=data.get('username'), 
        email=data.get('email'), 
        password_hash=generate_password_hash(data.get('password')),
        is_admin=False 
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Usuario registrado con éxito.'})

@app.route('/api/guardar_consumo', methods=['POST'])
def guardar_consumo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado. Inicie sesión.'}), 401

    data = request.get_json()
    
    try:
        tipo_servicio = Tipo_Servicio.query.filter_by(nombre_servicio=data['servicio_nombre']).first()
        if not tipo_servicio:
            return jsonify({'success': False, 'message': f"Servicio '{data['servicio_nombre']}' no encontrado."}), 404

        costo_valor = data.get('costo')
        fecha_obj = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
        
        nuevo_registro = Consumo(
            valor_consumo=float(data['consumo']),
            fecha_consumo=fecha_obj,
            costo_total=float(costo_valor) if costo_valor else None, 
            fk_id_usuario=session['user_id'], 
            fk_id_tipo_servicio=tipo_servicio.id_tipo_servicio 
        )
        
        db.session.add(nuevo_registro)
        
        generar_alerta_si_es_necesario(session['user_id'], nuevo_registro, tipo_servicio)
        actualizar_historial_anual(session['user_id'], nuevo_registro, tipo_servicio.nombre_servicio)
        
        if nuevo_registro.costo_total is not None:
            actualizar_ahorro_mensual(session['user_id'], fecha_obj, nuevo_registro)

        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Consumo registrado con éxito. Revisando alertas...'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error interno al guardar: {str(e)}'}), 500

@app.route('/api/dashboard_data')
def get_dashboard_data():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado.'}), 401

    try:
        user_id = session['user_id']
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        consumos_mensuales = db.session.query(
            Tipo_Servicio.nombre_servicio,
            extract('month', Consumo.fecha_consumo).label('mes'),
            func.sum(Consumo.valor_consumo).label('total_consumo')
        ).join(Tipo_Servicio).filter(
            Consumo.fk_id_usuario == user_id,
            extract('year', Consumo.fecha_consumo) == current_year
        ).group_by(Tipo_Servicio.nombre_servicio, 'mes').order_by('mes').all()
        
        distribucion_total = db.session.query(
            Tipo_Servicio.nombre_servicio,
            func.sum(Consumo.valor_consumo).label('total_general')
        ).join(Tipo_Servicio).filter(
            Consumo.fk_id_usuario == user_id,
            extract('year', Consumo.fecha_consumo) == current_year
        ).group_by(Tipo_Servicio.nombre_servicio).all()
        
        historial_anual = Consumo_Anual_Historico.query.filter_by(
            fk_id_usuario=user_id
        ).order_by(Consumo_Anual_Historico.anio.desc()).all()

        total_costo_mes_actual = db.session.query(
            func.sum(Consumo.costo_total)
        ).filter(
            Consumo.fk_id_usuario == user_id,
            extract('year', Consumo.fecha_consumo) == current_year,
            extract('month', Consumo.fecha_consumo) == current_month,
            Consumo.costo_total != None
        ).scalar() or 0.0
        
        
        fecha_hoy = date.today()
        fecha_mes_anterior = (fecha_hoy.replace(day=1) - timedelta(days=1))
        
        total_costo_mes_anterior = db.session.query(
            func.sum(Consumo.costo_total)
        ).filter(
            Consumo.fk_id_usuario == user_id,
            extract('year', Consumo.fecha_consumo) == fecha_mes_anterior.year,
            extract('month', Consumo.fecha_consumo) == fecha_mes_anterior.month,
            Consumo.costo_total != None
        ).scalar() or 0.0
        
        ahorro_estimado = 0.0
        if total_costo_mes_anterior > 0:
            ahorro_estimado = total_costo_mes_anterior - total_costo_mes_actual

        return jsonify({
            'success': True,
            'monthly_data': [
                {'servicio': r.nombre_servicio, 'mes': r.mes, 'total': r.total_consumo} 
                for r in consumos_mensuales
            ],
            'distribution_data': [
                {'servicio': r.nombre_servicio, 'total': r.total_general} 
                for r in distribucion_total
            ],
            'annual_history': [
                {
                    'anio': h.anio, 
                    'Electricidad': h.total_consumo_electricidad,
                    'Agua': h.total_consumo_agua,
                    'Gas': h.total_consumo_gas,
                    'Internet': h.total_consumo_internet
                } for h in historial_anual
            ],
            'total_cost_current_month': total_costo_mes_actual,
            'ahorro_estimado': ahorro_estimado
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error de servidor: {str(e)}'}), 500

@app.route('/api/get_alertas')
def get_alertas():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado.'}), 401
    
    try:
        alertas = Alerta.query.filter_by(
            fk_id_usuario=session['user_id']
        ).order_by(Alerta.fecha_creacion.desc()).all()
        
        servicios_map = {s.id_tipo_servicio: s.nombre_servicio for s in Tipo_Servicio.query.all()}
        
        return jsonify({
            'success': True,
            'alertas': [{
                'texto': r.texto_alerta, 
                'fecha': r.fecha_creacion.strftime('%Y-%m-%d'),
                'servicio': servicios_map.get(r.fk_id_tipo_servicio, 'General')
            } for r in alertas]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error de servidor: {str(e)}'}), 500


@app.route('/api/subir_factura', methods=['POST'])
def subir_factura():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado.'}), 401
        
    try:
        periodo = request.form.get('periodo')
        monto = request.form.get('monto')
        if not periodo or not monto:
            return jsonify({'success': False, 'message': 'Periodo y Monto son requeridos.'}), 400
            
        if 'facturaFile' not in request.files:
            return jsonify({'success': False, 'message': 'No se encontró el archivo.'}), 400
        
        file = request.files['facturaFile']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo.'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(f"user_{session['user_id']}_{periodo}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            
            nueva_factura = Factura(
                periodo=periodo,
                monto_total=float(monto),
                archivo_uri=filename,
                fk_id_usuario=session['user_id'],
                fecha_generada=datetime.strptime(f"{periodo}-01", '%Y-%m-%d').date()
            )
            db.session.add(nueva_factura)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Factura subida y registrada con éxito.'})
        else:
            return jsonify({'success': False, 'message': 'Tipo de archivo no permitido.'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error interno al subir: {str(e)}'}), 500

@app.route('/uploads/facturas/<filename>')
def download_factura(filename):
    if 'user_id' not in session:
        return redirect(url_for('inicio'))
        
    
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/guardar_evaluacion', methods=['POST'])
def guardar_evaluacion():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado.'}), 401
        
    data = request.get_json()
    
    try:
        calificacion = int(data.get('calificacion'))
        comentario = data.get('comentario')
        
        if not (1 <= calificacion <= 5):
            return jsonify({'success': False, 'message': 'La calificación debe ser entre 1 y 5.'}), 400
            
        nueva_evaluacion = Evaluacion(
            calificacion=calificacion,
            comentario=comentario,
            fk_id_usuario=session['user_id'],
            fecha_evaluacion=date.today()
        )
        db.session.add(nueva_evaluacion)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '¡Gracias por tu evaluación!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/api/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado.'}), 401
    
    data = request.get_json()
    user = Usuario.query.get(session['user_id'])
    
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado.'}), 404
    
    try:
        new_username = data.get('username')
        new_email = data.get('email')
        new_password = data.get('password')
        
        if not new_username or not new_email:
            return jsonify({'success': False, 'message': 'Nombre de usuario y email son requeridos.'}), 400
        
        if new_email != user.email:
            existing_user = Usuario.query.filter_by(email=new_email).first()
            if existing_user:
                return jsonify({'success': False, 'message': 'El nuevo email ya está en uso por otra cuenta.'}), 400
        
        user.nombre_usuario = new_username
        user.email = new_email
        
        if new_password:
            if not check_password_hash(user.password_hash, data.get('current_password')):
                return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta.'}), 403
            user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Perfil actualizado con éxito.', 'new_username': user.nombre_usuario, 'new_email': user.email})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error interno: {str(e)}'}), 500

@app.route('/terminos')
def terminos():
    return render_template('terminos.html')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Debes ser administrador para acceder a esta página.', 'danger')
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    all_users = Usuario.query.filter_by(is_admin=False).order_by(Usuario.nombre_usuario).all()
    return render_template('admin.html', all_users=all_users)

@app.route('/admin/view_user/<int:user_id>')
@admin_required
def admin_view_user(user_id):
    user = Usuario.query.get_or_404(user_id)
    if user.is_admin: 
        return redirect(url_for('admin_dashboard'))
        
    consumos = Consumo.query.filter_by(fk_id_usuario=user_id).order_by(Consumo.fecha_consumo.desc()).all()
    alertas = Alerta.query.filter_by(fk_id_usuario=user_id).order_by(Alerta.fecha_creacion.desc()).all()
    facturas = Factura.query.filter_by(fk_id_usuario=user_id).order_by(Factura.periodo.desc()).all()
    servicios = Tipo_Servicio.query.all() 
    
    return render_template('admin_user_details.html', user=user, consumos=consumos, alertas=alertas, facturas=facturas, servicios=servicios)

@app.route('/admin/add_consumo/<int:user_id>', methods=['POST'])
@admin_required
def admin_add_consumo(user_id):
    try:
        user = Usuario.query.get_or_404(user_id)
        
        servicio_id = request.form.get('servicio_id')
        fecha_str = request.form.get('fecha')
        consumo_val = request.form.get('consumo')
        costo_val = request.form.get('costo')

        tipo_servicio = Tipo_Servicio.query.get(servicio_id)
        if not tipo_servicio:
            flash('Servicio no válido.', 'danger')
            return redirect(url_for('admin_view_user', user_id=user_id))

        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        
        nuevo_registro = Consumo(
            valor_consumo=float(consumo_val),
            fecha_consumo=fecha_obj,
            costo_total=float(costo_val) if costo_val else None,
            fk_id_usuario=user_id,
            fk_id_tipo_servicio=tipo_servicio.id_tipo_servicio
        )
        db.session.add(nuevo_registro)
        
        generar_alerta_si_es_necesario(user_id, nuevo_registro, tipo_servicio)
        actualizar_historial_anual(user_id, nuevo_registro, tipo_servicio.nombre_servicio)
        
        if nuevo_registro.costo_total is not None:
            actualizar_ahorro_mensual(user_id, fecha_obj, nuevo_registro)
        
        db.session.commit()
        flash('Consumo añadido exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al añadir consumo: {str(e)}', 'danger')
        
    return redirect(url_for('admin_view_user', user_id=user_id))


@app.route('/admin/delete_consumo/<int:consumo_id>', methods=['POST'])
@admin_required
def admin_delete_consumo(consumo_id):
    consumo = Consumo.query.get_or_404(consumo_id)
    user_id = consumo.fk_id_usuario
    try:
        db.session.delete(consumo)
        db.session.commit()
        flash('Registro de consumo eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'danger')
        
    return redirect(url_for('admin_view_user', user_id=user_id))

@app.route('/admin/delete_alerta/<int:alerta_id>', methods=['POST'])
@admin_required
def admin_delete_alerta(alerta_id):
    alerta = Alerta.query.get_or_404(alerta_id)
    user_id = alerta.fk_id_usuario
    try:
        db.session.delete(alerta)
        db.session.commit()
        flash('Alerta eliminada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'danger')

    return redirect(url_for('admin_view_user', user_id=user_id))

@app.route('/admin/edit_consumo/<int:consumo_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_consumo(consumo_id):
    consumo = Consumo.query.get_or_404(consumo_id)
    servicios = Tipo_Servicio.query.all()
    user_id = consumo.fk_id_usuario 

    if request.method == 'POST':
        try:
            consumo.fk_id_tipo_servicio = request.form.get('servicio_id')
            consumo.fecha_consumo = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
            consumo.valor_consumo = float(request.form.get('consumo'))
            costo = request.form.get('costo')
            consumo.costo_total = float(costo) if costo else None
            
            db.session.commit()
            flash('Registro de consumo actualizado.', 'success')
            
            
            
            
            return redirect(url_for('admin_view_user', user_id=user_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar consumo: {str(e)}', 'danger')
            
            return render_template('admin_edit_consumo.html', consumo=consumo, servicios=servicios)
    
    
    return render_template('admin_edit_consumo.html', consumo=consumo, servicios=servicios)


@app.route('/admin/edit_alerta/<int:alerta_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_alerta(alerta_id):
    alerta = Alerta.query.get_or_404(alerta_id)
    user_id = alerta.fk_id_usuario

    if request.method == 'POST':
        try:
            alerta.texto_alerta = request.form.get('texto_alerta')
            
            db.session.commit()
            flash('Alerta actualizada.', 'success')
            return redirect(url_for('admin_view_user', user_id=user_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar alerta: {str(e)}', 'danger')
            return render_template('admin_edit_alerta.html', alerta=alerta)

    
    return render_template('admin_edit_alerta.html', alerta=alerta)
    

@app.route('/admin/add_alerta/<int:user_id>', methods=['POST'])
@admin_required
def admin_add_alerta(user_id):
    try:
        user = Usuario.query.get_or_404(user_id)
        
        texto_alerta = request.form.get('texto_alerta')
        servicio_id_str = request.form.get('servicio_id')

        if not texto_alerta:
            flash('El texto de la alerta no puede estar vacío.', 'danger')
            return redirect(url_for('admin_view_user', user_id=user_id))

        servicio_id = None
        if servicio_id_str:
            servicio_id = int(servicio_id_str)

        nueva_alerta = Alerta(
            texto_alerta=texto_alerta,
            fk_id_usuario=user_id,
            fk_id_tipo_servicio=servicio_id,
            fecha_creacion=date.today()
        )
        
        db.session.add(nueva_alerta)
        db.session.commit()
        flash('Alerta manual añadida exitosamente.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al añadir alerta: {str(e)}', 'danger')
        
    return redirect(url_for('admin_view_user', user_id=user_id))


@app.route('/admin/edit_factura/<int:factura_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_factura(factura_id):
    factura = Factura.query.get_or_404(factura_id)
    user_id = factura.fk_id_usuario

    if request.method == 'POST':
        try:
            factura.periodo = request.form.get('periodo')
            factura.monto_total = float(request.form.get('monto'))
            
            db.session.commit()
            flash('Factura actualizada.', 'success')
            return redirect(url_for('admin_view_user', user_id=user_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar factura: {str(e)}', 'danger')
            return render_template('admin_edit_factura.html', factura=factura)

    
    return render_template('admin_edit_factura.html', factura=factura)


@app.route('/admin/delete_factura/<int:factura_id>', methods=['POST'])
@admin_required
def admin_delete_factura(factura_id):
    factura = Factura.query.get_or_404(factura_id)
    user_id = factura.fk_id_usuario
    archivo_uri = factura.archivo_uri
    
    try:
        
        if archivo_uri:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], archivo_uri)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        
        db.session.delete(factura)
        db.session.commit()
        flash('Factura y archivo asociado eliminados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar factura: {str(e)}', 'danger')

    return redirect(url_for('admin_view_user', user_id=user_id))


with app.app_context():
    inicializar_db_con_datos_basicos()

if __name__ == '__main__':
    app.run(debug=True)