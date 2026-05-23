const DETAIL = (() => {
  let currentHash = null;

  function init() {
    const panel = document.querySelector('.detail-content');

    document.querySelector('.detail-close').addEventListener('click', close);
    document.querySelector('.detail-overlay').addEventListener('click', e => {
      if (e.target === e.currentTarget) close();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') close();
    });

    panel.addEventListener('click', ev => {
      const btn = ev.target.closest('[data-action]');
      if (btn) {
        const a = btn.dataset.action;
        if (a === 'pdf' && btn.dataset.pdf) {
          DATA.markAsRead(currentHash);
          window.open(btn.dataset.pdf, '_blank');
        } else if (a === 'dir' && btn.dataset.dir) {
          window.open(btn.dataset.dir, '_blank');
          DATA.copyToClipboardWithFeedback(btn.dataset.dir, btn);
        } else if (a === 'fav') {
          DATA.toggleFavorite(currentHash);
          const entry = DATA.getEntry(currentHash);
          btn.textContent = entry.favorite ? '♥' : '♡';
          btn.classList.toggle('active', entry.favorite);
        } else if (a === 'read') {
          DATA.toggleRead(currentHash);
          const entry = DATA.getEntry(currentHash);
          btn.textContent = entry.read ? '✓ Leído' : '⊙ No leído';
        } else if (a === 'oculto') {
          DATA.toggleOculto(currentHash);
          const entry = DATA.getEntry(currentHash);
          btn.textContent = entry.oculto ? '👁 Mostrar' : '🚫 Ocultar';
          btn.title = entry.oculto ? 'Mostrar' : 'Ocultar';
        }
        return;
      }

      const star = ev.target.closest('.star');
      if (star) {
        const starsWrap = star.closest('.card-stars');
        if (!starsWrap) return;
        const hash = starsWrap.dataset.hash;
        const rating = parseInt(star.dataset.rating);
        DATA.setRating(hash, rating);
        starsWrap.querySelectorAll('.star').forEach((st, i) => {
          const active = i < rating;
          st.classList.toggle('active', active);
          st.textContent = active ? '✦' : '✧';
        });
        return;
      }

      const remove = ev.target.closest('.remove');
      if (remove) {
        const tag = remove.dataset.tag;
        const entry = DATA.getEntry(currentHash);
        if (!entry) return;
        const newTags = (entry.tags || []).filter(t => t !== tag);
        DATA.setTags(currentHash, newTags);
        updateTags(DATA.getEntry(currentHash));
      }
    });

    panel.addEventListener('input', ev => {
      const textarea = ev.target.closest('#detail-notes');
      if (!textarea) return;
      const counter = document.getElementById('notes-counter');
      if (counter) counter.textContent = `${textarea.value.length} caracteres`;
      clearTimeout(textarea._saveTimer);
      textarea._saveTimer = setTimeout(() => {
        DATA.setNotes(textarea.dataset.hash, textarea.value);
      }, 500);
    });

    panel.addEventListener('keydown', ev => {
      const tagInput = ev.target.closest('#tag-input');
      if (!tagInput || (ev.key !== 'Enter' && ev.key !== ',')) return;
      ev.preventDefault();
      const val = tagInput.value.trim();
      if (!val) return;
      const entry = DATA.getEntry(tagInput.dataset.hash);
      if (!entry) return;
      const newTags = [...(entry.tags || []), val];
      DATA.setTags(tagInput.dataset.hash, newTags);
      tagInput.value = '';
      updateTags(DATA.getEntry(tagInput.dataset.hash));
    });
  }

  function refresh() {
    if (!currentHash) return;
    const entry = DATA.getEntry(currentHash);
    if (entry) render(entry);
    else close();
  }

  function open(hash) {
    const entry = DATA.getEntry(hash);
    if (!entry) return;
    currentHash = hash;
    render(entry);
    document.querySelector('.detail-overlay').classList.add('open');
    document.querySelector('.detail-panel').classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    document.querySelector('.detail-overlay').classList.remove('open');
    document.querySelector('.detail-panel').classList.remove('open');
    document.body.style.overflow = '';
    currentHash = null;
  }

  function renderTagItems(e) {
    return (e.tags || []).map(t =>
      `<span class="tag-item">${DATA.escapeHtml(t)} <span class="remove" data-tag="${DATA.escapeAttr(t)}">×</span></span>`
    ).join('');
  }

  function updateTags(entry) {
    const editor = document.querySelector('.tags-editor');
    if (!editor) return;
    const input = editor.querySelector('#tag-input');
    const frag = document.createRange().createContextualFragment(renderTagItems(entry));
    editor.innerHTML = '';
    editor.appendChild(frag);
    if (input) editor.appendChild(input);
  }

  function render(e) {
    const panel = document.querySelector('.detail-content');
    const hasPortada = !!e.portada;
    const placeholderType = ['suplemento','aventura','mapa','otro'].includes(e.tipo) ? e.tipo : 'otro';
    const imgSrc = hasPortada ? e.portada : `assets/placeholders/${placeholderType}.svg`;
    const imgClass = hasPortada ? '' : 'placeholder';
    const tipoLabel = {
      manual: '📖 Manual', suplemento: '📜 Suplemento', campaña: '⚔ Campaña',
      aventura: '🗡 Aventura', revista: '📰 Revista', documento: '📄 Documento',
      info: 'ℹ Info', musica: '🎵 Música', imagen: '🖼 Imagen',
      mapa: '🌍 Mapa', hoja_pj: '📋 Hoja PJ', pantalla: '🛡 Pantalla',
      otro: '📦 Otro',
    }[e.tipo] || '📄 Otro';
    const starsHtml = DATA.renderStars(e.rating || 0);
    const favIcon = e.favorite ? '♥' : '♡';
    const pdfPath = DATA.buildPdfPath(e);
    const dirPath = DATA.buildDirPath(e);
    const tagsHtml = renderTagItems(e);

    panel.innerHTML = `
      <img class="detail-cover ${imgClass}" src="${imgSrc}" alt="${DATA.escapeAttr(e.nombre_legible)}"
        onerror="this.src='assets/placeholders/${placeholderType}.svg'">
      <h2 class="detail-title">${DATA.escapeHtml(e.nombre_legible.replace(/\.pdf$/i, ''))}</h2>
      <div class="detail-subtitle">${e.juego || ''} ${e.edicion && e.edicion !== 'indeterminada' ? '· ' + e.edicion : ''}</div>
      <div class="detail-meta">
        <span class="tag">${tipoLabel}</span>
        ${e.escaneado ? '<span class="tag">🔍 Escaneado</span>' : '<span class="tag">💻 Digital</span>'}
        ${e.peso ? `<span class="tag">💾 ${e.peso}</span>` : ''}
        <span class="tag">🔒 ${e.confianza || 'media'}</span>
        <span class="tag">🗝 ${e.archivo_hash ? e.archivo_hash.substring(0, 12) + '…' : ''}</span>
      </div>
      <div class="detail-desc">${DATA.escapeHtml(e.descripcion || 'Sin descripción')}</div>
      ${e.justificacion ? `<div class="detail-just">📌 ${DATA.escapeHtml(e.justificacion)}</div>` : ''}

      <div class="detail-actions">
        <button class="card-btn pdf" data-action="pdf" data-pdf="${DATA.escapeAttr(pdfPath)}">📄 Abrir PDF</button>
        <button class="card-btn" data-action="dir" data-dir="${DATA.escapeAttr(dirPath)}" style="margin-left:4px;">📁 Carpeta</button>
        <div class="card-stars" data-hash="${e.archivo_hash}" style="display:inline-flex;font-size:1.3em;cursor:pointer;margin-left:8px;">${starsHtml}</div>
        <button class="card-btn fav-btn ${e.favorite ? 'active' : ''}" data-action="fav" style="font-size:1.3em;margin-left:auto;">${favIcon}</button>
        <button class="card-btn" data-action="read">${e.read ? '✓ Leído' : '⊙ No leído'}</button>
        <button class="card-btn" data-action="oculto" style="margin-left:4px;" title="${e.oculto ? 'Mostrar' : 'Ocultar'}">${e.oculto ? '👁 Mostrar' : '🚫 Ocultar'}</button>
      </div>

      <div class="detail-section detail-notes">
        <h3>✎ Notas personales</h3>
        <textarea id="detail-notes" placeholder="Escribe tus notas sobre este manuscrito..." data-hash="${e.archivo_hash}">${DATA.escapeHtml(e.notes || '')}</textarea>
        <div class="notes-counter" id="notes-counter">${(e.notes || '').length} caracteres</div>
      </div>

      <div class="detail-section">
        <h3>🏷 Tags</h3>
        <div class="tags-editor">
          ${tagsHtml}
          <input class="tag-input" id="tag-input" placeholder="Añadir tag…" data-hash="${e.archivo_hash}">
        </div>
      </div>

      <div class="detail-section">
        <h3>📋 Información adicional</h3>
        <table style="width:100%;font-size:0.85em;border-collapse:collapse;">
          ${e.destino ? `<tr><td style="padding:3px 8px;color:var(--ink-light);">Destino</td><td style="padding:3px 8px;">${DATA.escapeHtml(e.destino)}</td></tr>` : ''}
          ${e.nombre_legible ? `<tr><td style="padding:3px 8px;color:var(--ink-light);">Archivo</td><td style="padding:3px 8px;">${DATA.escapeHtml(e.nombre_legible.replace(/\.pdf$/i, ''))}</td></tr>` : ''}
          ${e.archivo_hash ? `<tr><td style="padding:3px 8px;color:var(--ink-light);">Hash</td><td style="padding:3px 8px;font-family:monospace;font-size:0.85em;">${e.archivo_hash}</td></tr>` : ''}
        </table>
      </div>
    `;
  }





  return { init, open, close, refresh };
})();
