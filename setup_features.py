import os, re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
print("📖 app.py leído")

# 1. AGREGAR CAMPOS AL MODELO File
old = "    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)\n\nclass AdminLog"
new = """    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    is_favorite = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(64), nullable=True)

class AdminLog"""
if old in content:
    content = content.replace(old, new)
    print("✅ Campos nuevos en File")
else:
    print("⚠️ No encontré el modelo File")

# 2. AGREGAR MODELO ShareLink
share = """
class ShareLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    file = db.relationship('File', backref='share_links')

"""
marker = "# ==================== FUNCIONES ===================="
if marker in content and 'class ShareLink' not in content:
    content = content.replace(marker, share + marker)
    print("✅ ShareLink agregado")
else:
    print("⚠️ ShareLink ya existe o no encontré marcador")

# 3. REEMPLAZAR api_files
old_api = r"@app\.route\('/api/files'\)\n@login_required\ndef api_files\(\):.*?return jsonify\(\{'files': files_list\}\)"
new_api = """@app.route('/api/files')
@login_required
def api_files():
    mostrar_papelera = request.args.get('trash') == '1'
    mostrar_favoritos = request.args.get('favorites') == '1'
    query = File.query.filter_by(user_id=current_user.id)
    if mostrar_papelera:
        query = query.filter(File.deleted_at.isnot(None))
    elif mostrar_favoritos:
        query = query.filter_by(is_favorite=True).filter(File.deleted_at.is_(None))
    else:
        query = query.filter(File.deleted_at.is_(None))
    archivos = query.order_by(File.upload_date.desc()).all()
    def get_icon(tipo):
        icons = {'imagen':'🖼️','video':'🎬','audio':'🎵','documento':'📄','comprimido':'📦','otro':'📎'}
        return icons.get(tipo, '📎')
    files_list = [{
        'id': f.id, 'name': f.filename,
        'size': format_file_size(f.file_size), 'sizeBytes': f.file_size,
        'type': f.file_type, 'icon': get_icon(f.file_type),
        'date': f.upload_date.strftime('%d/%m/%Y'),
        'is_favorite': f.is_favorite,
        'deleted_at': f.deleted_at.strftime('%d/%m/%Y') if f.deleted_at else None,
        'share_token': f.share_token
    } for f in archivos]
    return jsonify({'files': files_list})"""
if re.search(old_api, content, re.DOTALL):
    content = re.sub(old_api, new_api, content, flags=re.DOTALL)
    print("✅ api_files actualizado")
else:
    print("⚠️ No encontré api_files")

# 4. REEMPLAZAR delete Y AGREGAR RUTAS NUEVAS
old_delete = r"@app\.route\('/delete/<int:file_id>'\, methods=\['GET', 'POST'\]\).*?return redirect\(url_for\('dashboard'\)\)"
new_routes = """@app.route('/delete/<int:file_id>', methods=['GET', 'POST'])
@login_required
def delete(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id and not current_user.is_admin():
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'No autorizado'})
        flash('No autorizado', 'error')
        return redirect(url_for('dashboard'))
    archivo.deleted_at = datetime.utcnow()
    db.session.commit()
    if request.method == 'POST':
        return jsonify({'success': True, 'message': 'Archivo movido a la papelera'})
    flash('Archivo movido a la papelera', 'success')
    return redirect(url_for('dashboard'))

@app.route('/trash')
@login_required
def trash():
    archivos = File.query.filter_by(user_id=current_user.id).filter(File.deleted_at.isnot(None)).all()
    return render_template('trash.html', user=current_user, files=archivos)

@app.route('/trash/delete/<int:file_id>', methods=['POST'])
@login_required
def trash_delete(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id:
        return jsonify({'success': False})
    path = os.path.join(app.config['UPLOAD_FOLDER'], archivo.saved_name)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(archivo)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/trash/restore/<int:file_id>', methods=['POST'])
@login_required
def trash_restore(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id:
        return jsonify({'success': False})
    archivo.deleted_at = None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/trash/empty', methods=['POST'])
@login_required
def trash_empty():
    archivos = File.query.filter_by(user_id=current_user.id).filter(File.deleted_at.isnot(None)).all()
    for archivo in archivos:
        path = os.path.join(app.config['UPLOAD_FOLDER'], archivo.saved_name)
        if os.path.exists(path):
            os.remove(path)
        db.session.delete(archivo)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/favorites')
@login_required
def favorites():
    archivos = File.query.filter_by(user_id=current_user.id, is_favorite=True).filter(File.deleted_at.is_(None)).all()
    return render_template('favorites.html', user=current_user, files=archivos)

@app.route('/toggle_favorite/<int:file_id>', methods=['POST'])
@login_required
def toggle_favorite(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id:
        return jsonify({'success': False})
    archivo.is_favorite = not archivo.is_favorite
    db.session.commit()
    return jsonify({'success': True, 'is_favorite': archivo.is_favorite})

@app.route('/share/<int:file_id>', methods=['POST'])
@login_required
def share_file(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id:
        return jsonify({'success': False})
    if not archivo.share_token:
        archivo.share_token = str(uuid.uuid4()).replace('-', '')
        db.session.commit()
    link = request.host_url + 'p/' + archivo.share_token
    return jsonify({'success': True, 'link': link})

@app.route('/unshare/<int:file_id>', methods=['POST'])
@login_required
def unshare_file(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id:
        return jsonify({'success': False})
    archivo.share_token = None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/p/<token>')
def public_file(token):
    archivo = File.query.filter_by(share_token=token).first_or_404()
    if archivo.deleted_at:
        return "Archivo no disponible", 404
    return render_template('public_file.html', file=archivo)

@app.route('/preview/<int:file_id>')
@login_required
def preview(file_id):
    archivo = File.query.get_or_404(file_id)
    if archivo.user_id != current_user.id and not current_user.is_admin():
        return "No autorizado", 403
    return send_from_directory(app.config['UPLOAD_FOLDER'], archivo.saved_name)"""

if re.search(old_delete, content, re.DOTALL):
    content = re.sub(old_delete, new_routes, content, flags=re.DOTALL)
    print("✅ Rutas nuevas agregadas")
else:
    print("⚠️ No encontré la ruta delete, agregando al final antes del admin...")
    content = content.replace(
        "# ==================== PANEL DE ADMINISTRACIÓN ====================",
        new_routes + "\n\n# ==================== PANEL DE ADMINISTRACIÓN ===================="
    )
    print("✅ Rutas agregadas antes del panel admin")

# 5. GUARDAR app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("💾 app.py guardado")

# 6. CREAR trash.html
trash_html = """{% extends "base.html" %}
{% block title %}Papelera{% endblock %}
{% block content %}
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;">
    <h2 style="font-size:1.3rem;font-weight:700;">🗑️ Papelera</h2>
    <button onclick="emptyTrash()" style="padding:0.5rem 1rem;background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#fca5a5;border-radius:10px;cursor:pointer;">Vaciar papelera</button>
</div>
<div class="file-table-wrap">
    <div class="ft-head" style="grid-template-columns:2.5fr 0.8fr 1fr 130px;">
        <div>Nombre</div><div>Tamaño</div><div>Eliminado</div><div>Acciones</div>
    </div>
    {% if files %}
        {% for f in files %}
        <div class="ft-row" id="row-{{f.id}}" style="grid-template-columns:2.5fr 0.8fr 1fr 130px;opacity:0.75;">
            <div class="ft-name">
                <span class="ft-ico">{% if f.file_type == 'imagen' %}🖼️{% elif f.file_type == 'video' %}🎬{% elif f.file_type == 'audio' %}🎵{% elif f.file_type == 'documento' %}📄{% elif f.file_type == 'comprimido' %}📦{% else %}📎{% endif %}</span>
                <span style="text-decoration:line-through;color:#7a8aaa;">{{f.filename}}</span>
            </div>
            <div style="color:#7a8aaa;font-size:0.8rem;">{% set s=f.file_size %}{% if s<1024 %}{{s}} B{% elif s<1048576 %}{{(s/1024)|round(1)}} KB{% elif s<1073741824 %}{{(s/1048576)|round(1)}} MB{% else %}{{(s/1073741824)|round(2)}} GB{% endif %}</div>
            <div style="color:#7a8aaa;font-size:0.8rem;">{{f.deleted_at.strftime('%d/%m/%Y') if f.deleted_at else '—'}}</div>
            <div class="ft-actions">
                <button class="fa-btn" onclick="restoreFile({{f.id}})">♻️ Restaurar</button>
                <button class="fa-btn" onclick="deleteForever({{f.id}})" style="color:#fca5a5;">🔥</button>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty-state"><div style="font-size:3rem;margin-bottom:1rem">🗑️</div><h3>La papelera está vacía</h3><p style="color:#7a8aaa;">Los archivos eliminados aparecerán aquí</p></div>
    {% endif %}
</div>
<style>
.file-table-wrap{background:#151e2d;border:1px solid rgba(255,255,255,0.07);border-radius:16px;overflow:hidden}
.ft-head{display:grid;padding:0.8rem 1.2rem;background:#0d1320;font-size:0.7rem;text-transform:uppercase;color:#7a8aaa;border-bottom:1px solid rgba(255,255,255,0.07)}
.ft-row{display:grid;padding:0.8rem 1.2rem;align-items:center;border-bottom:1px solid rgba(255,255,255,0.05)}
.ft-name{display:flex;align-items:center;gap:0.8rem}.ft-ico{font-size:1.5rem}
.ft-actions{display:flex;gap:0.3rem;justify-content:flex-end}
.fa-btn{background:transparent;border:none;cursor:pointer;font-size:0.85rem;padding:0.3rem 0.6rem;border-radius:6px;color:#e8edf5;transition:all 0.2s}
.fa-btn:hover{background:rgba(255,255,255,0.1)}.empty-state{text-align:center;padding:3rem}
</style>
<script>
async function restoreFile(id){const r=await fetch('/trash/restore/'+id,{method:'POST'});const d=await r.json();if(d.success){document.getElementById('row-'+id).remove();showToast('✅ Restaurado','success');}}
async function deleteForever(id){if(!confirm('¿Eliminar para siempre?'))return;const r=await fetch('/trash/delete/'+id,{method:'POST'});const d=await r.json();if(d.success){document.getElementById('row-'+id).remove();showToast('🔥 Eliminado','success');}}
async function emptyTrash(){if(!confirm('¿Vaciar toda la papelera?'))return;const r=await fetch('/trash/empty',{method:'POST'});const d=await r.json();if(d.success)location.reload();}
</script>
{% endblock %}"""

with open('templates/trash.html', 'w', encoding='utf-8') as f:
    f.write(trash_html)
print("✅ trash.html creado")

# 7. CREAR favorites.html
fav_html = """{% extends "base.html" %}
{% block title %}Favoritos{% endblock %}
{% block content %}
<div style="margin-bottom:1.5rem;"><h2 style="font-size:1.3rem;font-weight:700;">⭐ Favoritos</h2></div>
<div class="file-table-wrap">
    <div class="ft-head" style="grid-template-columns:2.5fr 0.8fr 1fr 0.8fr 90px;">
        <div>Nombre</div><div>Tamaño</div><div>Fecha</div><div>Tipo</div><div>Acciones</div>
    </div>
    {% if files %}
        {% for f in files %}
        <div class="ft-row" id="row-{{f.id}}" style="grid-template-columns:2.5fr 0.8fr 1fr 0.8fr 90px;">
            <div class="ft-name">
                <span class="ft-ico">{% if f.file_type == 'imagen' %}🖼️{% elif f.file_type == 'video' %}🎬{% elif f.file_type == 'audio' %}🎵{% elif f.file_type == 'documento' %}📄{% elif f.file_type == 'comprimido' %}📦{% else %}📎{% endif %}</span>
                <span>{{f.filename}}</span>
            </div>
            <div style="color:#7a8aaa;font-size:0.8rem;">{% set s=f.file_size %}{% if s<1024 %}{{s}} B{% elif s<1048576 %}{{(s/1024)|round(1)}} KB{% elif s<1073741824 %}{{(s/1048576)|round(1)}} MB{% else %}{{(s/1073741824)|round(2)}} GB{% endif %}</div>
            <div style="color:#7a8aaa;font-size:0.8rem;">{{f.upload_date.strftime('%d/%m/%Y')}}</div>
            <div><span class="type-badge {{f.file_type}}">{{f.file_type}}</span></div>
            <div class="ft-actions">
                <button class="fa-btn" onclick="removeFav({{f.id}})">⭐</button>
                <button class="fa-btn" onclick="window.location='/download/{{f.id}}'">⬇️</button>
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty-state"><div style="font-size:3rem;margin-bottom:1rem">⭐</div><h3>Sin favoritos aún</h3><p style="color:#7a8aaa;">Marca archivos con ⭐ desde el dashboard</p></div>
    {% endif %}
</div>
<style>
.file-table-wrap{background:#151e2d;border:1px solid rgba(255,255,255,0.07);border-radius:16px;overflow:hidden}
.ft-head{display:grid;padding:0.8rem 1.2rem;background:#0d1320;font-size:0.7rem;text-transform:uppercase;color:#7a8aaa;border-bottom:1px solid rgba(255,255,255,0.07)}
.ft-row{display:grid;padding:0.8rem 1.2rem;align-items:center;border-bottom:1px solid rgba(255,255,255,0.05);transition:background 0.2s}
.ft-row:hover{background:rgba(59,130,246,0.05)}.ft-name{display:flex;align-items:center;gap:0.8rem}.ft-ico{font-size:1.5rem}
.ft-actions{display:flex;gap:0.3rem;justify-content:flex-end}
.fa-btn{background:transparent;border:none;cursor:pointer;font-size:1rem;padding:0.3rem;border-radius:6px;transition:all 0.2s}
.fa-btn:hover{background:rgba(255,255,255,0.1)}
.type-badge{display:inline-block;padding:0.2rem 0.6rem;border-radius:20px;font-size:0.7rem}
.type-badge.imagen{background:rgba(34,197,94,0.15);color:#4ade80}.type-badge.video{background:rgba(6,182,212,0.15);color:#22d3ee}
.type-badge.audio{background:rgba(139,92,246,0.15);color:#a78bfa}.type-badge.documento{background:rgba(59,130,246,0.15);color:#60a5fa}
.type-badge.comprimido{background:rgba(245,158,11,0.15);color:#fbbf24}.type-badge.otro{background:rgba(156,163,175,0.15);color:#9ca3af}
.empty-state{text-align:center;padding:3rem}
</style>
<script>
async function removeFav(id){const r=await fetch('/toggle_favorite/'+id,{method:'POST'});const d=await r.json();if(d.success){const row=document.getElementById('row-'+id);row.style.opacity='0';row.style.transition='opacity 0.3s';setTimeout(()=>row.remove(),300);showToast('Quitado de favoritos','info');}}
</script>
{% endblock %}"""

with open('templates/favorites.html', 'w', encoding='utf-8') as f:
    f.write(fav_html)
print("✅ favorites.html creado")

# 8. CREAR public_file.html
public_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{file.filename}} — Mi Nube</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:sans-serif;background:#0a0c10;color:#e8edf5;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}
        .card{background:#151e2d;border:1px solid #1e2a3a;border-radius:20px;padding:2.5rem;max-width:500px;width:100%;text-align:center}
        .logo{font-size:1.2rem;font-weight:700;color:#60a5fa;margin-bottom:2rem}
        .file-icon{font-size:4rem;margin-bottom:1rem}
        .file-name{font-size:1.1rem;font-weight:600;word-break:break-word;margin-bottom:0.5rem}
        .file-meta{font-size:0.8rem;color:#7a8aaa;margin-bottom:2rem}
        .dl-btn{display:inline-block;background:linear-gradient(135deg,#3b82f6,#2563eb);color:white;padding:0.8rem 2rem;border-radius:12px;text-decoration:none;font-weight:600}
    </style>
</head>
<body>
<div class="card">
    <div class="logo">☁️ Mi Nube</div>
    <div class="file-icon">{% if file.file_type == 'imagen' %}🖼️{% elif file.file_type == 'video' %}🎬{% elif file.file_type == 'audio' %}🎵{% elif file.file_type == 'documento' %}📄{% elif file.file_type == 'comprimido' %}📦{% else %}📎{% endif %}</div>
    <div class="file-name">{{file.filename}}</div>
    <div class="file-meta">Compartido · {{(file.file_size/1048576)|round(1)}} MB</div>
    <a href="/download/{{file.id}}" class="dl-btn">⬇️ Descargar</a>
</div>
</body>
</html>"""

with open('templates/public_file.html', 'w', encoding='utf-8') as f:
    f.write(public_html)
print("✅ public_file.html creado")

print()
print("🎉 ¡Script terminado! Revisa los mensajes arriba.")