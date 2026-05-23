const CARD = (() => {
  let onDetail = null, onPdfOpen = null, onFolderClick = null;
  let viewMode = localStorage.getItem('aquelarre_view_mode') || 'grid';
  let browseMode = localStorage.getItem('aquelarre_browse_mode') || 'folder';

  function init(callbacks) {
    onDetail = callbacks.onDetail || null;
    onPdfOpen = callbacks.onPdfOpen || null;
    onFolderClick = callbacks.onFolderClick || null;
  }

  function setViewMode(mode) {
    viewMode = mode;
    localStorage.setItem('aquelarre_view_mode', mode);
  }

  function getViewMode() { return viewMode; }

  function setBrowseMode(mode) {
    browseMode = mode;
    localStorage.setItem('aquelarre_browse_mode', mode);
  }

  function getBrowseMode() { return browseMode; }

  function render(entries, container) {
    if (!entries || entries.length === 0) {
      container.className = 'card-grid empty';
      container.innerHTML = '<span>🔍 No se encontraron manuscritos con esos criterios</span>';
      return;
    }
    const isList = viewMode === 'list';
    container.className = 'card-grid' + (isList ? ' list-view' : '');
    container.innerHTML = entries.map(e => isList ? renderCardList(e) : renderCard(e)).join('');
    bindEvents(container);
  }

  function renderWithFolders(folders, entries, container) {
    const isList = viewMode === 'list';
    container.className = 'card-grid folder-mode' + (isList ? ' list-view' : '');
    let html = '';
    for (const f of folders) {
      html += isList ? renderFolderCardList(f) : renderFolderCard(f);
    }
    html += entries.map(e => isList ? renderCardList(e) : renderCard(e)).join('');
    if (!html) {
      container.className = 'card-grid empty';
      container.innerHTML = '<span>🔍 Esta categoría está vacía</span>';
      return;
    }
    container.innerHTML = html;
    bindEvents(container);
    bindFolderEvents(container);
  }

  function renderFolderCard(f) {
    return `<div class="card card-folder" data-folder-path="${DATA.escapeAttr(f.path)}" data-folder-depth="${f.depth}">
      <div class="card-folder-icon">${f.icon}</div>
      <div class="card-folder-title">${DATA.escapeHtml(f.label)}</div>
      <div class="card-folder-count">${f.count} archivos</div>
    </div>`;
  }

  function renderFolderCardList(f) {
    return `<div class="card card-list card-folder" data-folder-path="${DATA.escapeAttr(f.path)}" data-folder-depth="${f.depth}">
      <div class="card-list-img" style="background:var(--bg-paper-dark);font-size:2em;display:flex;align-items:center;justify-content:center;">${f.icon}</div>
      <div class="card-list-body">
        <div class="card-title">${DATA.escapeHtml(f.label)}</div>
        <div class="card-meta"><span class="tag">📁 Carpeta</span></div>
        <div class="card-list-desc">${f.count} archivos en esta categoría</div>
      </div>
      <div class="card-list-actions" style="justify-content:center;min-width:60px;">
        <span style="font-size:1.5em;color:var(--gold-light);">›</span>
      </div>
    </div>`;
  }

  function getPlaceholderSrc(e) {
    const t = ['suplemento','aventura','mapa','otro'].includes(e.tipo) ? e.tipo : 'otro';
    return `assets/placeholders/${t}.svg`;
  }

  function renderCard(e) {
    const hasPortada = !!e.portada;
    const placeholderSvg = getPlaceholderSrc(e);
    const imgSrc = hasPortada ? e.portada : placeholderSvg;
    const favClass = e.favorite ? 'active' : '';
    const readToggleIcon = e.read ? '✓' : '⊙';
    const favIcon = e.favorite ? '♥' : '♡';
    const starsHtml = DATA.renderStars(e.rating || 0);

    const tipoLabel = {
      manual: '📖', suplemento: '📜', campaña: '⚔',
      aventura: '🗡', revista: '📰', documento: '📄',
      info: 'ℹ', musica: '🎵', imagen: '🖼',
      mapa: '🌍', hoja_pj: '📋', pantalla: '🛡',
      otro: '📦',
    }[e.tipo] || '📄';
    const edLabel = e.edicion && e.edicion !== 'indeterminada' ? `· ${e.edicion}` : '';

    const desc = (e.descripcion || '').substring(0, 120);
    const descSuffix = (e.descripcion || '').length > 120 ? '…' : '';

    const pdfPath = DATA.buildPdfPath(e);
    const dirPath = DATA.buildDirPath(e);

    return `<div class="card${e.favorite ? ' favorite' : ''}" data-hash="${e.archivo_hash}">
      <div class="card-img-wrap">
        <img src="${imgSrc}" loading="lazy" alt="${DATA.escapeAttr(e.nombre_legible)}"
          onerror="this.src='${placeholderSvg}'">
        <div class="card-badges">
          <span class="card-badge ${e.read ? 'read' : 'unread'}">${e.read ? '✓ Leído' : '⊙ No leído'}</span>
          ${e.favorite ? '<span class="card-badge fav">♥</span>' : ''}
        </div>
      </div>
      <div class="card-body">
        <div class="card-title">${DATA.escapeHtml(stripExt(e.nombre_legible))}</div>
        <div class="card-meta">
          <span class="tag">${tipoLabel} ${e.tipo}</span>
          ${edLabel ? `<span class="tag">${edLabel}</span>` : ''}
          ${e.escaneado ? '<span class="tag">🔍 Scan</span>' : ''}
          ${e.peso ? `<span class="tag">💾 ${e.peso}</span>` : ''}
        </div>
        <div class="card-desc">${DATA.escapeHtml(desc)}${descSuffix}</div>
        <div class="card-footer">
          <div class="card-stars" data-hash="${e.archivo_hash}">${starsHtml}</div>
          <div class="card-actions">
            <button class="card-btn fav-btn ${favClass}" data-action="fav" title="Favorito">${favIcon}</button>
            <button class="card-btn" data-action="read" title="${e.read ? 'Marcar no leído' : 'Marcar leído'}">${readToggleIcon}</button>
            <button class="card-btn" data-action="detail" title="Detalle">📋</button>
            <button class="card-btn" data-action="dir" data-dir="${DATA.escapeAttr(dirPath)}" title="Abrir carpeta">📁</button>
            <button class="card-btn" data-action="oculto" title="${e.oculto ? 'Mostrar' : 'Ocultar'}">${e.oculto ? '👁' : '🚫'}</button>
            <button class="card-btn pdf" data-action="pdf" data-pdf="${DATA.escapeAttr(pdfPath)}" title="Abrir PDF">📄</button>
          </div>
        </div>
      </div>
    </div>`;
  }

  function renderCardList(e) {
    const hasPortada = !!e.portada;
    const placeholderSvg = getPlaceholderSrc(e);
    const imgSrc = hasPortada ? e.portada : placeholderSvg;
    const favClass = e.favorite ? 'active' : '';
    const readToggleIcon = e.read ? '✓' : '⊙';
    const favIcon = e.favorite ? '♥' : '♡';
    const starsHtml = DATA.renderStars(e.rating || 0);
    const tipoLabel = {
      manual: '📖', suplemento: '📜', campaña: '⚔',
      aventura: '🗡', revista: '📰', documento: '📄',
      info: 'ℹ', musica: '🎵', imagen: '🖼',
      mapa: '🌍', hoja_pj: '📋', pantalla: '🛡',
      otro: '📦',
    }[e.tipo] || '📄';
    const edLabel = e.edicion && e.edicion !== 'indeterminada' ? `· ${e.edicion}` : '';
    const pdfPath = DATA.buildPdfPath(e);
    const dirPath = DATA.buildDirPath(e);
    return `<div class="card card-list${e.favorite ? ' favorite' : ''}" data-hash="${e.archivo_hash}">
      <div class="card-list-img">
        <img src="${imgSrc}" loading="lazy" alt="${DATA.escapeAttr(e.nombre_legible)}" onerror="this.src='${placeholderSvg}'">
      </div>
      <div class="card-list-body">
        <div class="card-title">${DATA.escapeHtml(stripExt(e.nombre_legible))}</div>
        <div class="card-meta">
          <span class="tag">${tipoLabel} ${e.tipo}</span>
          ${edLabel ? `<span class="tag">${edLabel}</span>` : ''}
          ${e.escaneado ? '<span class="tag">🔍 Scan</span>' : ''}
          ${e.peso ? `<span class="tag">💾 ${e.peso}</span>` : ''}
          <span class="tag ${e.read ? 'read' : 'unread'}">${e.read ? '✓ Leído' : '⊙ No leído'}</span>
          ${e.favorite ? '<span class="tag fav">♥ Favorito</span>' : ''}
        </div>
        <div class="card-list-desc">${DATA.escapeHtml((e.descripcion || '').substring(0, 200))}</div>
      </div>
      <div class="card-list-actions">
        <div class="card-stars" data-hash="${e.archivo_hash}">${starsHtml}</div>
        <div class="card-actions">
          <button class="card-btn fav-btn ${favClass}" data-action="fav" title="Favorito">${favIcon}</button>
          <button class="card-btn" data-action="read" title="${e.read ? 'Marcar no leído' : 'Marcar leído'}">${readToggleIcon}</button>
          <button class="card-btn" data-action="detail" title="Detalle">📋</button>
          <button class="card-btn" data-action="dir" data-dir="${DATA.escapeAttr(dirPath)}" title="Abrir carpeta">📁</button>
          <button class="card-btn" data-action="oculto" title="${e.oculto ? 'Mostrar' : 'Ocultar'}">${e.oculto ? '👁' : '🚫'}</button>
          <button class="card-btn pdf" data-action="pdf" data-pdf="${DATA.escapeAttr(pdfPath)}" title="Abrir PDF">📄</button>
        </div>
      </div>
    </div>`;
  }



  function bindEvents(container) {
    if (container._bound) return;
    container._bound = true;
    container.addEventListener('click', e => {
      const card = e.target.closest('.card');
      if (!card) return;
      const hash = card.dataset.hash;

      const star = e.target.closest('.star');
      if (star) {
        const rating = parseInt(star.dataset.rating);
        DATA.setRating(hash, rating);
        const starsWrap = star.closest('.card-stars');
        starsWrap.querySelectorAll('.star').forEach((st, i) => {
          const active = i < rating;
          st.classList.toggle('active', active);
          st.textContent = active ? '✦' : '✧';
        });
        return;
      }

      const btn = e.target.closest('[data-action]');
      if (!btn) return;
      const action = btn.dataset.action;

      if (action === 'fav') {
        DATA.toggleFavorite(hash);
        const entry = DATA.getEntry(hash);
        card.classList.toggle('favorite', entry.favorite);
        btn.textContent = entry.favorite ? '♥' : '♡';
        btn.classList.toggle('active', entry.favorite);
        const badge = card.querySelector('.card-badge.fav');
        if (entry.favorite && !badge) {
          card.querySelector('.card-badges').insertAdjacentHTML('beforeend', '<span class="card-badge fav">♥</span>');
        } else if (!entry.favorite && badge) {
          badge.remove();
        }
        const readBadge = card.querySelector('.card-badge.read, .card-badge.unread');
        if (readBadge) {
          readBadge.className = `card-badge ${entry.read ? 'read' : 'unread'}`;
          readBadge.textContent = entry.read ? '✓ Leído' : 'No leído';
        }
        return;
      }

      if (action === 'detail' && onDetail) {
        onDetail(hash);
        return;
      }

      if (action === 'read') {
        DATA.toggleRead(hash);
        const entry = DATA.getEntry(hash);
        const badge = card.querySelector('.card-badge.read, .card-badge.unread');
        if (badge) {
          badge.className = `card-badge ${entry.read ? 'read' : 'unread'}`;
          badge.textContent = entry.read ? '✓ Leído' : '⊙ No leído';
        }
        btn.textContent = entry.read ? '✓' : '⊙';
        btn.title = entry.read ? 'Marcar no leído' : 'Marcar leído';
        return;
      }

      if (action === 'dir') {
        const path = btn.dataset.dir;
        if (path) {
          window.open(path, '_blank');
          DATA.copyToClipboardWithFeedback(path, btn);
        }
        return;
      }

      if (action === 'oculto') {
        DATA.toggleOculto(hash);
        const entry = DATA.getEntry(hash);
        btn.textContent = entry.oculto ? '👁' : '🚫';
        btn.title = entry.oculto ? 'Mostrar' : 'Ocultar';
        APP.refresh();
        return;
      }

      if (action === 'pdf') {
        const path = btn.dataset.pdf;
        if (path) {
          DATA.markAsRead(hash);
          window.open(path, '_blank');
        }
        return;
      }
    });

    container.addEventListener('mouseover', e => {
      const star = e.target.closest('.star');
      if (!star) return;
      const starsWrap = star.closest('.card-stars');
      if (!starsWrap) return;
      const rating = parseInt(star.dataset.rating);
      starsWrap.querySelectorAll('.star').forEach((st, i) => {
        st.classList.toggle('active', i < rating);
      });
    });
    container.addEventListener('mouseout', e => {
      const starsWrap = e.target.closest('.card-stars');
      if (!starsWrap) return;
      if (starsWrap.contains(e.relatedTarget)) return;
      const hash = starsWrap.dataset.hash;
      const entry = DATA.getEntry(hash);
      const currentRating = entry ? entry.rating : 0;
      starsWrap.querySelectorAll('.star').forEach((st, i) => {
        st.classList.toggle('active', i < currentRating);
      });
    });
  }

  function bindFolderEvents(container) {
    if (container._boundFolder) return;
    container._boundFolder = true;
    container.addEventListener('click', e => {
      const card = e.target.closest('.card-folder');
      if (!card || !onFolderClick) return;
      const path = card.dataset.folderPath;
      if (path !== undefined) onFolderClick(path);
    });
  }

  function stripExt(name) {
    return name ? name.replace(/\.(pdf|PDF)$/, '') : '';
  }

  return { init, render, renderWithFolders, setViewMode, getViewMode, setBrowseMode, getBrowseMode };
})();
