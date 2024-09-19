from flask import Flask, request, redirect, render_template, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Inicializa la base de datos
def init_db():
    conn = sqlite3.connect('horas_sociales.db')
    cursor = conn.cursor()

    # Crear la tabla usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('alumno', 'maestro', 'manager'))
        )
    ''')

    # Crear la tabla registros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_horas TEXT NOT NULL,
            fecha DATE NOT NULL,
            horas INTEGER NOT NULL,
            usuario_id INTEGER,
            estado TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # Crear la tabla proyectos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL 
        )
    ''')

    # Insertar usuarios específicos
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (username, password, role)
        VALUES
        ('karen', '1234', 'alumno'),
        ('chris', '12345', 'maestro'),
        ('mngr', '7412', 'manager')
    ''')

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('horas_sociales.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user_id'] = user[0]
        session['role'] = user[3]
        if user[3] == 'alumno':
            return redirect(url_for('index_alumno'))
        elif user[3] == 'maestro':
            return redirect(url_for('index_maestro'))
        elif user[3] == 'manager':
            return redirect(url_for('manager'))
    else:
        return render_template('login.html', error='Usuario o contraseña incorrectos')

@app.route('/index_alumno')
def index_alumno():
    if 'role' in session and session['role'] == 'alumno':
        return render_template('index.html')
    else:
        return redirect(url_for('index'))

@app.route('/index_maestro')
def index_maestro():
    if 'role' in session and session['role'] == 'maestro':
        return render_template('iniciom.html')
    else:
        return redirect(url_for('index'))

@app.route('/solicitudes', methods=['GET'])
def solicitudes():
    if 'role' in session and session['role'] == 'maestro':
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT registros.id, proyectos.nombre AS tipo_horas, registros.fecha, registros.horas, usuarios.username
            FROM registros
            JOIN usuarios ON registros.usuario_id = usuarios.id
            JOIN proyectos ON registros.tipo_horas = proyectos.id
            WHERE registros.estado IS NULL
        ''')
        solicitudes = cursor.fetchall()
        conn.close()

        return render_template('solicitudes.html', solicitudes=solicitudes)
    else:
        return redirect(url_for('index'))


@app.route('/aceptar/<int:registro_id>', methods=['POST'])
def aceptar(registro_id):
    if 'role' in session and session['role'] == 'maestro':
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE registros
            SET estado = 'aceptado'
            WHERE id = ?
        ''', (registro_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('solicitudes'))
    else:
        return redirect(url_for('index'))

@app.route('/rechazar/<int:registro_id>', methods=['POST'])
def rechazar(registro_id):
    if 'role' in session and session['role'] == 'maestro':
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE registros
            SET estado = 'rechazado'
            WHERE id = ?
        ''', (registro_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('solicitudes'))
    else:
        return redirect(url_for('index'))

@app.route('/mostrar')
def mostrar():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    conn = sqlite3.connect('horas_sociales.db')
    cursor = conn.cursor()

    # Mostrar registros confirmados y pendientes
    cursor.execute('''
        SELECT registros.id, proyectos.nombre AS tipo_horas, registros.fecha, registros.horas
        FROM registros
        JOIN proyectos ON registros.tipo_horas = proyectos.id
        WHERE registros.usuario_id = ? AND registros.estado = 'aceptado'
    ''', (session['user_id'],))
    registros_confirmados = cursor.fetchall()

    cursor.execute('''
        SELECT registros.id, proyectos.nombre AS tipo_horas, registros.fecha, registros.horas
        FROM registros
        JOIN proyectos ON registros.tipo_horas = proyectos.id
        WHERE registros.usuario_id = ? AND registros.estado IS NULL
    ''', (session['user_id'],))
    solicitudes_pendientes = cursor.fetchall()

    conn.close()
    return render_template('tabla.html', 
                           registros_confirmados=registros_confirmados, 
                           solicitudes_pendientes=solicitudes_pendientes)


@app.route('/acerca-de')
def acerca_de():
    return render_template('acerca-de.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/formulario')
def formulario():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    conn = sqlite3.connect('horas_sociales.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, nombre FROM proyectos')
    proyectos = cursor.fetchall()
    conn.close()

    return render_template('formulario.html', proyectos=proyectos)

@app.route('/submit', methods=['POST'])
def submit():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    proyecto_id = request.form['proyecto']
    fecha = request.form['fecha']
    horas = request.form['horas']

    conn = sqlite3.connect('horas_sociales.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO registros (tipo_horas, fecha, horas, usuario_id)
        VALUES (?, ?, ?, ?)
    ''', (proyecto_id, fecha, horas, session['user_id']))
    conn.commit()
    conn.close()

    return redirect('/mostrar')

@app.route('/alumnos')
def alumnos():
    if 'role' in session and session['role'] == 'maestro':
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username FROM usuarios WHERE role = 'alumno'
        ''')
        alumnos = cursor.fetchall()
        conn.close()

        return render_template('alumnos.html', alumnos=alumnos)
    else:
        return redirect(url_for('index'))

@app.route('/horas_alumno/<int:alumno_id>')
def horas_alumno(alumno_id):
    if 'role' in session and session['role'] == 'maestro':
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM registros
            WHERE usuario_id = ? AND estado = 'aceptado'
        ''', (alumno_id,))
        horas = cursor.fetchall()
        conn.close()

        return render_template('horas_alumno.html', horas=horas)
    else:
        return redirect(url_for('index'))

@app.route('/agregar-proyectos')
def agregar_proyectos():
    if 'role' in session and session['role'] == 'maestro':
        return render_template('agregar_proyectos.html')
    else:
        return redirect(url_for('index'))

@app.route('/add_project', methods=['POST'])
def add_project():
    if 'role' in session and session['role'] == 'maestro':
        nombre_proyecto = request.form['nombre_proyecto']
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO proyectos (nombre)
                VALUES (?)
            ''', (nombre_proyecto,))
            conn.commit()
        except sqlite3.IntegrityError:
            return 'El proyecto ya existe.'
        conn.close()
        return redirect(url_for('agregar_proyectos'))
    else:
        return redirect(url_for('index'))

@app.route('/manager')
def manager():
    if 'role' in session and session['role'] == 'manager':
        return render_template('manager.html')
    else:
        return redirect(url_for('index'))

@app.route('/agregar_usuario', methods=['GET', 'POST'])
def agregar_usuario():
    if 'role' in session and session['role'] == 'manager':
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            conn = sqlite3.connect('horas_sociales.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usuarios (username, password, role)
                VALUES (?, ?, ?)
            ''', (username, password, role))
            conn.commit()
            conn.close()
            return redirect(url_for('manager'))
        return render_template('agregar_usuario.html')
    else:
        return redirect(url_for('index'))

@app.route('/eliminar_usuario', methods=['GET', 'POST'])
def eliminar_usuario():
    if 'role' in session and session['role'] == 'manager':
        if request.method == 'POST':
            username = request.form['username']
            print(f"Intentando eliminar el usuario: {username}")
            conn = sqlite3.connect('horas_sociales.db')
            cursor = conn.cursor()

            # Verifica si el usuario existe antes de intentar eliminarlo
            cursor.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user:
                cursor.execute('DELETE FROM usuarios WHERE username = ?', (username,))
                conn.commit()
                print(f"Usuario {username} eliminado.")
            else:
                print(f"Usuario {username} no encontrado.")
            conn.close()

            return redirect(url_for('manager'))
        return render_template('eliminar_usuario.html')
    else:
        return redirect(url_for('index'))

@app.route('/usuarios')
def usuarios():
    if 'role' in session and session['role'] == 'manager':
        conn = sqlite3.connect('horas_sociales.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username, role, password FROM usuarios')
        usuarios = cursor.fetchall()
        conn.close()

        # Convertir la lista de tuplas a una lista de diccionarios
        usuarios = [{'username': u[0], 'role': u[1], 'password': u[2]} for u in usuarios]

        return render_template('usuarios.html', usuarios=usuarios)
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=3000)