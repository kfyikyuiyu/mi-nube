"""
MI NUBE - APLICACIÓN COMPLETA CON PANEL DE ADMIN
"""

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid

# ==================== CONFIGURACIÓN ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mi-clave-secreta-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5 GB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/avatars', exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para continuar'

# ==================== MODELOS ====================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin, owner
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.String(200), nullable=True)
    ban_until = db.Column(db.DateTime, nullable=True)
    avatar = db.Column(db.String(200), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    files = db.relationship('File', backref='owner', lazy=True)
    
    def is_admin(self):
        return self.role in ['admin', 'owner']
    
    def is_owner(self):
        return self.role == 'owner'
    
    def is_banned_active(self):
        if not self.is_banned:
            return False
        if self.ban_until and self.ban_until > datetime.utcnow():
            return True
        if self.ban_until and self.ban_until <= datetime.utcnow():
            self.is_banned = False
            self.ban_reason = None
            self.ban_until = None
            db.session.commit()
            return False
        return self.is_banned

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    saved_name = db.Column(db.String(500), unique=True, nullable=False)
    file_type = db.Column(db.String(50), default='otro')
    file_extension = db.Column(db.String(20), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    admin_name = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    target_user = db.Column(db.String(80), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== FUNCIONES ====================
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user and user.is_banned_active():
        return None
    return user

def get_file_type(filename):
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if extension in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']:
        return 'imagen'
    elif extension in ['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm']:
        return 'video'
    elif extension in ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']:
        return 'audio'
    elif extension in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv']:
        return 'documento'
    elif extension in ['zip', 'rar', '7z', 'tar', 'gz']:
        return 'comprimido'
    else:
        return 'otro'

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def owner_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_owner():
            flash('Acceso denegado. Se requieren permisos de owner.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def log_admin_action(action, target_user=None, details=None):
    if current_user.is_authenticated and current_user.is_admin():
        log = AdminLog(
            admin_id=current_user.id,
            admin_name=current_user.username,
            action=action,
            target_user=target_user,
            details=details
        )
        db.session.add(log)
        db.session.commit()

def create_owner():
    owner = User.query.filter_by(role='owner').first()
    if not owner:
        owner = User(
            username='admin',
            email='admin@minube.com',
            password=generate_password_hash('admin123', method='pbkdf2:sha256'),
            role='owner'
        )
        db.session.add(owner)
        db.session.commit()
        print("=" * 50)
        print("✅ USUARIO OWNER CREADO")
        print("   Email: admin@minube.com")
        print("   Contraseña: admin123")
        print("=" * 50)

# ==================== RUTAS PRINCIPALES ====================
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_banned_active():
            logout_user()
            flash('Tu cuenta ha sido suspendida.', 'error')
            return redirect(url_for('login'))
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if not username or not email or not password:
            flash('Todos los campos son obligatorios', 'error')
            return render_template('register.html')
        
        if password != confirm:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado', 'error')
            return render_template('register.html')
        
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed, role='user')
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('¡Registro exitoso! Ahora inicia sesión', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            if user.is_banned_active():
                flash('Tu cuenta está suspendida', 'error')
                return redirect(url_for('login'))
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash(f'¡Bienvenido {user.username}!', 'success')
            if user.is_admin():
                log_admin_action("Inicio de sesión", target_user=user.username)
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_banned_active():
        logout_user()
        flash('Tu cuenta está suspendida', 'error')
        return redirect(url_for('login'))
    
    archivos = File.query.filter_by(user_id=current_user.id).order_by(File.upload_date.desc()).all()
    total = sum(f.file_size for f in archivos)
    return render_template('dashboard.html', user=current_user, files=archivos, total=format_file_size(total))

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', user=current_user)

# ==================== ARCHIVOS ====================
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if current_user.is_banned_active():
        return jsonify({'success': False, 'message': 'Tu cuenta está suspendida'})
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No hay archivo en la solicitud'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'})
    
    try:
        original = secure_filename(file.filename)
        ext = original.rsplit('.', 1)[1].lower() if '.' in original else ''
        unico = str(uuid.uuid4()) + '_' + original
        path = os.path.join(app.config['UPLOAD_FOLDER'], unico)
        file.save(path)
        size = os.path.getsize(path)
        tipo = get_file_type(original)
        
        nuevo = File(
            filename=original,
            saved_name=unico,
            file_type=tipo,
            file_extension=ext,
            file_size=size,
            user_id=current_user.id
        )
        db.session.add(nuevo)
        db.session.commit()
        
        if current_user.is_admin():
            log_admin_action("Subió archivo", target_user=current_user.username, details=original)
        
        return jsonify({'success': True, 'message': f'{original} subido correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<int:file_id>')
@login_required
def download(file_id):
    if current_user.is_banned_active():
        flash('Tu cuenta está suspendida', 'error')
        return redirect(url_for('dashboard'))
    
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id and not current_user.is_admin():
        flash('No autorizado', 'error')
        return redirect(url_for('dashboard'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], archivo.saved_name, as_attachment=True, download_name=archivo.filename)

@app.route('/delete/<int:file_id>', methods=['GET', 'POST'])
@login_required
def delete(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id and not current_user.is_admin():
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'No autorizado'})
        flash('No autorizado', 'error')
        return redirect(url_for('dashboard'))
    
    path = os.path.join(app.config['UPLOAD_FOLDER'], archivo.saved_name)
    if os.path.exists(path):
        os.remove(path)
    
    nombre = archivo.filename
    db.session.delete(archivo)
    db.session.commit()
    
    if current_user.is_admin():
        log_admin_action("Eliminó archivo", target_user=current_user.username, details=nombre)
    
    if request.method == 'POST':
        return jsonify({'success': True, 'message': 'Archivo eliminado'})
    flash('Archivo eliminado', 'success')
    return redirect(url_for('dashboard'))

# ==================== API ENDPOINTS ====================
@app.route('/api/files')
@login_required
def api_files():
    archivos = File.query.filter_by(user_id=current_user.id).order_by(File.upload_date.desc()).all()
    
    def get_icon(tipo):
        icons = {
            'imagen': '🖼️',
            'video': '🎬',
            'audio': '🎵',
            'documento': '📄',
            'comprimido': '📦',
            'otro': '📎'
        }
        return icons.get(tipo, '📎')
    
    files_list = [{
        'id': f.id,
        'name': f.filename,
        'size': format_file_size(f.file_size),
        'sizeBytes': f.file_size,
        'type': f.file_type,
        'icon': get_icon(f.file_type),
        'date': f.upload_date.strftime('%d/%m/%Y')
    } for f in archivos]
    
    return jsonify({'files': files_list})

# ==================== PANEL DE ADMINISTRACIÓN ====================
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    if current_user.is_banned_active():
        logout_user()
        flash('Tu cuenta está suspendida', 'error')
        return redirect(url_for('login'))
    
    total_users = User.query.count()
    total_files = File.query.count()
    total_admins = User.query.filter(User.role.in_(['admin', 'owner'])).count()
    total_banned = User.query.filter_by(is_banned=True).count()
    users = User.query.order_by(User.created_at.desc()).all()
    logs = AdminLog.query.order_by(AdminLog.timestamp.desc()).limit(50).all()
    
    return render_template('admin_panel.html', 
                         total_users=total_users,
                         total_files=total_files,
                         total_admins=total_admins,
                         total_banned=total_banned,
                         users=users,
                         logs=logs)

@app.route('/admin/user/<int:user_id>')
@login_required
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    user_files = File.query.filter_by(user_id=user.id).order_by(File.upload_date.desc()).all()
    total_space = sum(f.file_size for f in user_files)
    
    return render_template('admin_user_detail.html', 
                         target_user=user,
                         files=user_files,
                         total_space=format_file_size(total_space))

@app.route('/admin/change_role/<int:user_id>', methods=['POST'])
@login_required
@owner_required
def admin_change_role(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.is_owner():
        flash('No se puede cambiar el rol del owner principal', 'error')
        return redirect(url_for('admin_panel'))
    
    new_role = request.form.get('role')
    if new_role in ['user', 'admin']:
        old_role = user.role
        user.role = new_role
        db.session.commit()
        log_admin_action(f"Cambió rol de usuario", target_user=user.username, details=f"De {old_role} a {new_role}")
        flash(f'Rol de {user.username} cambiado a {new_role}', 'success')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_ban_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.is_owner():
        flash('No se puede banear al owner principal', 'error')
        return redirect(url_for('admin_panel'))
    
    if user.id == current_user.id:
        flash('No puedes banear tu propia cuenta', 'error')
        return redirect(url_for('admin_panel'))
    
    ban_days = int(request.form.get('ban_days', 0))
    ban_reason = request.form.get('ban_reason', 'Sin razón especificada')
    
    if ban_days > 0:
        user.is_banned = True
        user.ban_until = datetime.utcnow() + timedelta(days=ban_days)
        user.ban_reason = ban_reason
        db.session.commit()
        log_admin_action(f"Baneó usuario", target_user=user.username, details=f"Por {ban_days} días. Razón: {ban_reason}")
        flash(f'Usuario {user.username} baneado por {ban_days} día(s)', 'success')
    else:
        flash('Especifica una duración válida', 'error')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/unban_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_unban_user(user_id):
    user = User.query.get_or_404(user_id)
    
    user.is_banned = False
    user.ban_reason = None
    user.ban_until = None
    db.session.commit()
    
    log_admin_action(f"Desbaneó usuario", target_user=user.username)
    flash(f'Usuario {user.username} ha sido desbaneado', 'success')
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@owner_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.is_owner():
        flash('No se puede eliminar al owner principal', 'error')
        return redirect(url_for('admin_panel'))
    
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta desde aquí', 'error')
        return redirect(url_for('admin_panel'))
    
    for file in user.files:
        path = os.path.join(app.config['UPLOAD_FOLDER'], file.saved_name)
        if os.path.exists(path):
            os.remove(path)
    
    username = user.username
    log_admin_action(f"Eliminó usuario", target_user=username, details="Todos sus archivos eliminados")
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Usuario {username} y todos sus archivos han sido eliminados', 'success')
    return redirect(url_for('admin_panel'))

# ==================== CREAR TABLAS ====================
with app.app_context():
    db.create_all()
    create_owner()
    print("=" * 50)
    print("✅ MI NUBE - SERVIDOR LISTO")
    print("📁 http://127.0.0.1:5000")
    print("👑 Admin: admin@minube.com / admin123")
    print("=" * 50)

if __name__ == '__main__':
    app.run(debug=True, port=5000)