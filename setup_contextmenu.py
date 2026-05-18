import os

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar menú contextual y upload a carpeta
menu_css = """
/* Menú clic derecho */
.context-menu {
    position: fixed;
    background: #151e2d;
    border: 1px solid #2d3a4a;
    border-radius: 10px;
    padding: 0.4rem;
    z-index: 99999;
    min-width: 180px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    display: none;
}
.context-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 0.8rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: background 0.2s;
}
.context-item:hover {
    background: rgba(59,130,246,0.15);
    color: #60a5fa;
}
.context-divider {
    height: 1px;
    background: #1e2a3a;
    margin: 0.3rem 0;
}
/* Modal carpeta */
.folder-modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 99998;
    align-items: center;
    justify-content: center;
}
.folder-modal-box {
    background: #151e2d;
    border: 1px solid #1e2a3a;
    border-radius: 16px;
    padding: 2rem;
    width: 380px;
}
"""

# Agregar CSS antes del cierre de </style>
content = content.replace('</style>\n\n<script>', menu_css + '</style>\n\n<script>')

# 2. Agregar HTML del menú y modal antes de </script> final... no, antes de {% endblock %}
menu_html = """
<!-- Menú clic derecho -->
<div class="context-menu" id="contextMenu">
    <div class="context-item" onclick="ctxNewFolder()">📁 Nueva carpeta</div>
    <div class="context-item" onclick="ctxUpload()">⬆️ Subir archivo aquí</div>
    <div class="context-divider"></div>
    <div class="context-item" onclick="window.location.href='/folders'">📂 Ver carpetas</div>
</div>

<!-- Modal nueva carpeta -->
<div class="folder-modal" id="folderModal">
    <div class="folder-modal-box">
        <h3 style="margin-bottom:1rem;">📁 Nueva carpeta</h3>
        <input id="folderNameInput" type="text" placeholder="Nombre de la carpeta"
            style="width:100%;padding:0.7rem;background:#0d1320;border:1px solid #2d3a4a;border-radius:10px;color:#e8edf5;font-size:0.9rem;margin-bottom:1rem;outline:none;">
        <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
            <button onclick="closeFolderModal()" style="padding:0.5rem 1rem;background:transparent;border:1px solid #2d3a4a;color:#9ca3af;border-radius:8px;cursor:pointer;">Cancelar</button>
            <button onclick="createFolderFromMenu()" style="padding:0.5rem 1rem;background:linear-gradient(135deg,#3b82f6,#2563eb);border:none;color:white;border-radius:8px;cursor:pointer;font-weight:600;">Crear</button>
        </div>
    </div>
</div>

<!-- Modal mover archivo -->
<div class="folder-modal" id="moveModal">
    <div class="folder-modal-box">
        <h3 style="margin-bottom:1rem;">📂 Mover a carpeta</h3>
        <div id="moveFolderList" style="max-height:250px;overflow-y:auto;margin-bottom:1rem;"></div>
        <div style="display:flex;gap:0.5rem;justify-content:flex-end;">
            <button onclick="closeMoveModal()" style="padding:0.5rem 1rem;background:transparent;border:1px solid #2d3a4a;color:#9ca3af;border-radius:8px;cursor:pointer;">Cancelar</button>
        </div>
    </div>
</div>
"""

content = content.replace('<div id="previewModal"', menu_html + '\n<div id="previewModal"')

# 3. Agregar funciones JS nuevas antes de closePreview
new_js = """
    // ========== MENÚ CLIC DERECHO ==========
    let moveFileId = null;

    document.addEventListener('contextmenu', function(e) {
        const row = e.target.closest('.ft-row');
        if (row) {
            e.preventDefault();
            const fileId = row.querySelector('.fa-btn[onclick*="deleteFile"]')?.getAttribute('onclick')?.match(/\\d+/)?.[0];
            if (fileId) {
                showFileContextMenu(e.clientX, e.clientY, fileId, row);
                return;
            }
        }
        const zone = e.target.closest('#uploadZone, .file-table-wrap, .main-content');
        if (zone) {
            e.preventDefault();
            showContextMenu(e.clientX, e.clientY);
        }
    });

    document.addEventListener('click', function() {
        document.getElementById('contextMenu').style.display = 'none';
    });

    function showContextMenu(x, y) {
        const menu = document.getElementById('contextMenu');
        menu.innerHTML = `
            <div class="context-item" onclick="ctxNewFolder()">📁 Nueva carpeta</div>
            <div class="context-item" onclick="ctxUpload()">⬆️ Subir archivo</div>
            <div class="context-divider"></div>
            <div class="context-item" onclick="window.location.href='/folders'">📂 Ver carpetas</div>
        `;
        menu.style.display = 'block';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
    }

    function showFileContextMenu(x, y, fileId, row) {
        const fileName = row.querySelector('.ft-name span:last-child')?.textContent || '';
        const menu = document.getElementById('contextMenu');
        menu.innerHTML = `
            <div class="context-item" style="color:#9ca3af;font-size:0.75rem;cursor:default;">${fileName.substring(0,25)}${fileName.length>25?'...':''}</div>
            <div class="context-divider"></div>
            <div class="context-item" onclick="previewFromCtx(${fileId}, event)">👁️ Vista previa</div>
            <div class="context-item" onclick="moveFileCtx(${fileId})">📂 Mover a carpeta</div>
            <div class="context-item" onclick="shareFile(${fileId})">🔗 Copiar link</div>
            <div class="context-item" onclick="toggleFavorite(${fileId}, {textContent:''})">⭐ Favorito</div>
            <div class="context-divider"></div>
            <div class="context-item" onclick="window.location='/download/${fileId}'">⬇️ Descargar</div>
            <div class="context-item" onclick="deleteFile(${fileId})" style="color:#fca5a5;">🗑️ Mover a papelera</div>
        `;
        menu.style.display = 'block';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
    }

    function previewFromCtx(id, e) {
        const files_data = files;
        const f = files_data.find(x => x.id === id);
        if(f) previewFile(f.id, f.type, f.name);
        document.getElementById('contextMenu').style.display = 'none';
    }

    function ctxNewFolder() {
        document.getElementById('contextMenu').style.display = 'none';
        document.getElementById('folderModal').style.display = 'flex';
        document.getElementById('folderNameInput').focus();
    }

    function ctxUpload() {
        document.getElementById('contextMenu').style.display = 'none';
        document.getElementById('fileInput').click();
    }

    function closeFolderModal() {
        document.getElementById('folderModal').style.display = 'none';
        document.getElementById('folderNameInput').value = '';
    }

    async function createFolderFromMenu() {
        const name = document.getElementById('folderNameInput').value.trim();
        if (!name) return;
        const r = await fetch('/folders/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name})
        });
        const d = await r.json();
        if (d.success) {
            closeFolderModal();
            showToast('📁 Carpeta creada', 'success');
        } else {
            showToast('Error al crear carpeta', 'error');
        }
    }

    async function moveFileCtx(id) {
        moveFileId = id;
        document.getElementById('contextMenu').style.display = 'none';
        const r = await fetch('/api/folders');
        const d = await r.json();
        const list = document.getElementById('moveFolderList');
        if (d.folders.length === 0) {
            list.innerHTML = '<p style="color:#7a8aaa;text-align:center;padding:1rem;">No tienes carpetas aún.<br>Crea una con clic derecho.</p>';
        } else {
            list.innerHTML = d.folders.map(f => `
                <div onclick="doMoveFile(${f.id})" style="padding:0.8rem;border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:0.8rem;transition:background 0.2s;"
                    onmouseover="this.style.background='rgba(59,130,246,0.1)'"
                    onmouseout="this.style.background='transparent'">
                    <span style="font-size:1.5rem;">📁</span>
                    <span>${f.name}</span>
                </div>
            `).join('');
        }
        document.getElementById('moveModal').style.display = 'flex';
    }

    async function doMoveFile(folderId) {
        const r = await fetch('/files/move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({file_id: moveFileId, folder_id: folderId})
        });
        const d = await r.json();
        if (d.success) {
            closeMoveModal();
            showToast('📂 Archivo movido a carpeta', 'success');
            loadFiles();
        }
    }

    function closeMoveModal() {
        document.getElementById('moveModal').style.display = 'none';
        moveFileId = null;
    }

    document.getElementById('folderNameInput')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') createFolderFromMenu();
        if (e.key === 'Escape') closeFolderModal();
    });

"""

content = content.replace('    async function toggleFavorite', new_js + '    async function toggleFavorite')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ dashboard.html actualizado")

# Agregar también botón de mover en ft-actions
content2 = open('templates/dashboard.html', 'r', encoding='utf-8').read()
old_actions = """<button class="fa-btn" onclick="previewFile(${file.id},'${file.type}','${file.name}')">👁️</button>
                    <button class="fa-btn" onclick="toggleFavorite(${file.id},this)">${file.is_favorite?'⭐':'☆'}</button>
                    <button class="fa-btn" onclick="shareFile(${file.id})">🔗</button>
                    <button class="fa-btn" onclick="downloadFile(${file.id})">⬇️</button>
                    <button class="fa-btn" onclick="deleteFile(${file.id})">🗑️</button>"""

new_actions = """<button class="fa-btn" title="Preview" onclick="previewFile(${file.id},'${file.type}','${file.name}')">👁️</button>
                    <button class="fa-btn" title="Favorito" onclick="toggleFavorite(${file.id},this)">${file.is_favorite?'⭐':'☆'}</button>
                    <button class="fa-btn" title="Mover" onclick="moveFileCtx(${file.id})">📂</button>
                    <button class="fa-btn" title="Compartir" onclick="shareFile(${file.id})">🔗</button>
                    <button class="fa-btn" title="Descargar" onclick="downloadFile(${file.id})">⬇️</button>
                    <button class="fa-btn" title="Papelera" onclick="deleteFile(${file.id})">🗑️</button>"""

if old_actions in content2:
    content2 = content2.replace(old_actions, new_actions)
    print("✅ Botón mover agregado")
else:
    print("⚠️ No encontré los botones exactos")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content2)

print()
print("🎉 ¡Listo! Corre actualizar_pagina.bat")