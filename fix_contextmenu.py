with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_js = """
    // ========== MENU CLIC DERECHO ==========
    let moveFileId = null;

    document.addEventListener('contextmenu', function(e) {
        const row = e.target.closest('.ft-row');
        if (row) {
            e.preventDefault();
            const btns = row.querySelectorAll('.fa-btn');
            let fileId = null;
            btns.forEach(b => {
                const m = b.getAttribute('onclick') ? b.getAttribute('onclick').match(/\\d+/) : null;
                if(m) fileId = m[0];
            });
            if (fileId) { showFileContextMenu(e.clientX, e.clientY, fileId, row); return; }
        }
        const zone = e.target.closest('.main-content');
        if (zone) { e.preventDefault(); showContextMenu(e.clientX, e.clientY); }
    });

    document.addEventListener('click', function() {
        const m = document.getElementById('contextMenu');
        if(m) m.style.display = 'none';
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
        const fileName = row.querySelector('.ft-name span:last-child') ? row.querySelector('.ft-name span:last-child').textContent : '';
        const menu = document.getElementById('contextMenu');
        menu.innerHTML = `
            <div class="context-item" style="color:#9ca3af;font-size:0.75rem;cursor:default;">${fileName.substring(0,25)}</div>
            <div class="context-divider"></div>
            <div class="context-item" onclick="moveFileCtx(${fileId})">📂 Mover a carpeta</div>
            <div class="context-item" onclick="shareFile(${fileId})">🔗 Copiar link</div>
            <div class="context-divider"></div>
            <div class="context-item" onclick="window.location='/download/${fileId}'">⬇️ Descargar</div>
            <div class="context-item" onclick="deleteFile(${fileId})" style="color:#fca5a5;">🗑️ Papelera</div>
        `;
        menu.style.display = 'block';
        menu.style.left = x + 'px';
        menu.style.top = y + 'px';
    }

    function ctxNewFolder() {
        document.getElementById('contextMenu').style.display = 'none';
        document.getElementById('folderModal').style.display = 'flex';
        setTimeout(() => document.getElementById('folderNameInput').focus(), 100);
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
            list.innerHTML = '<p style="color:#7a8aaa;text-align:center;padding:1rem;">No tienes carpetas.<br>Crea una con clic derecho.</p>';
        } else {
            list.innerHTML = d.folders.map(f => `
                <div onclick="doMoveFile(${f.id})"
                    style="padding:0.8rem;border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:0.8rem;"
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

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { closeFolderModal(); closeMoveModal(); }
    });

"""

if 'contextmenu' not in content:
    content = content.replace('    async function toggleFavorite', new_js + '    async function toggleFavorite')
    print("✅ JS del menu insertado")
else:
    print("⚠️ contextmenu ya existe")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("💾 Guardado")