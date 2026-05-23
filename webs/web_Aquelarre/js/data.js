const DATA = (() => {
  const LS_SHOW_OCULTOS = 'aquelarre_show_ocultos';
  let catalog = [];
  let dynamics = {};
  let merged = [];
  let _catalogError = false;
  let _showOcultos = (() => {
    try { return localStorage.getItem(LS_SHOW_OCULTOS) === 'true'; }
    catch { return false; }
  })();

  function _getCatalog() {
    return typeof CATALOGO_DATA !== 'undefined' ? CATALOGO_DATA : null;
  }

  function getLibraryId() {
    const c = _getCatalog();
    return (c && c.id) || 'aquelarre';
  }
  function _lsKey() { return `biblio_data_${getLibraryId()}`; }

  function isDirVisible(dirPath) {
    if (!dirPath) return true;
    const clean = dirPath.replace(/\/$/, '');
    const catalogData = _getCatalog() || {};
    const dv = catalogData.dir_visible || (typeof DIR_VISIBLE !== 'undefined' ? DIR_VISIBLE : {});
    const parts = clean.split('/');
    for (let i = 0; i < parts.length; i++) {
      const sub = parts.slice(0, i + 1).join('/');
      if (dv[sub] === false) return false;
    }
    return true;
  }

  function init() {
    const data = _getCatalog() || {};
    catalog = Array.isArray(data.clasificaciones) ? data.clasificaciones :
              Array.isArray(data) ? data : [];

    if (!_getCatalog()) {
      _catalogError = 'no_file';
    } else if (catalog.length === 0) {
      _catalogError = 'empty_or_invalid';
    } else {
      _catalogError = false;
    }

    const version = data.format_version;
    if (typeof version !== 'number') {
      console.warn("catalogo.js sin versionado — formato antiguo (v0)");
    } else if (version > 1) {
      console.warn("catalogo.js versión", version, "más nueva que la web");
    }

    loadDynamics();
    merge();
    return merged;
  }

  function loadDynamics() {
    try {
      dynamics = JSON.parse(localStorage.getItem(_lsKey())) || {};
    } catch { dynamics = {}; }
  }

  function saveDynamics() {
    localStorage.setItem(_lsKey(), JSON.stringify(dynamics));
  }

  function merge() {
    merged = catalog.map(entry => {
      const dyn = dynamics[entry.archivo_hash] || {};
      return {
        ...entry,
        rating: dyn.rating ?? 0,
        favorite: dyn.favorite ?? false,
        read: dyn.read ?? false,
        oculto: entry.oculto === true ? true : (dyn.oculto ?? false),
        notes: dyn.notes ?? '',
        tags: dyn.tags ?? [],
        lastRead: dyn.lastRead ?? null,
        addedDate: dyn.addedDate ?? (dyn.lastRead || new Date().toISOString()),
      };
    });
  }

  function getLibraryName() {
    const data = _getCatalog() || {};
    return data.nombre_biblioteca || '';
  }
  function getUrlBase() {
    const data = _getCatalog() || {};
    return data.url_base || '../Aquelarre_pak/';
  }
  function getFormatVersion() {
    const data = _getCatalog() || {};
    return data.format_version;
  }
  function getCatalogError() { return _catalogError; }

  function updateEntry(hash, updates) {
    const dyn = dynamics[hash] || {};
    Object.assign(dyn, updates);
    dynamics[hash] = dyn;
    saveDynamics();
    merge();
  }

  function setRating(hash, rating) {
    updateEntry(hash, { rating });
  }

  function toggleFavorite(hash) {
    const entry = merged.find(e => e.archivo_hash === hash);
    if (!entry) return;
    updateEntry(hash, { favorite: !entry.favorite });
  }

  function toggleRead(hash) {
    const entry = merged.find(e => e.archivo_hash === hash);
    if (!entry) return;
    updateEntry(hash, { read: !entry.read, lastRead: !entry.read ? new Date().toISOString() : entry.lastRead });
  }

  function toggleOculto(hash) {
    const entry = merged.find(e => e.archivo_hash === hash);
    if (!entry) return;
    updateEntry(hash, { oculto: !entry.oculto });
  }

  function markAsRead(hash) {
    const entry = merged.find(e => e.archivo_hash === hash);
    if (!entry) return;
    if (!entry.read) {
      updateEntry(hash, { read: true, lastRead: new Date().toISOString() });
    }
  }

  function setNotes(hash, notes) {
    updateEntry(hash, { notes });
  }

  function setTags(hash, tags) {
    updateEntry(hash, { tags });
  }

  function getEntry(hash) {
    return merged.find(e => e.archivo_hash === hash);
  }

  function getAll() {
    const visible = merged.filter(e => isDirVisible(e.destino || ''));
    return _showOcultos ? visible : visible.filter(e => !e.oculto);
  }

  function setShowOcultos(val) {
    _showOcultos = !!val;
    try { localStorage.setItem(LS_SHOW_OCULTOS, _showOcultos); } catch {}
  }

  function getShowOcultos() { return _showOcultos; }

  function buildPdfPath(entry) {
    const dest = (entry.destino || '').replace(/\/?$/, '/');
    return `${getUrlBase()}${dest}${entry.nombre_legible}`;
  }

  function buildDirPath(entry) {
    const dest = (entry.destino || '').replace(/\/?$/, '/');
    const a = document.createElement('a');
    a.href = `${getUrlBase()}${dest}`;
    return a.href;
  }

  function exportUserData() {
    const data = {
      version: 1,
      exportedAt: new Date().toISOString(),
      dynamics: dynamics,
      settings: {
        theme: localStorage.getItem('aquelarre_theme') || 'medieval',
        cardSize: localStorage.getItem('aquelarre_card_size') || 'normal',
        viewMode: localStorage.getItem('aquelarre_view_mode') || 'grid',
        browseMode: localStorage.getItem('aquelarre_browse_mode') || 'folder',
        showOcultos: _showOcultos,
      },
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const date = new Date().toISOString().slice(0, 10);
    a.download = `archivum_data_${date}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function importUserData(jsonStr) {
    try {
      const data = JSON.parse(jsonStr);
      if (!data || data.version !== 1) {
        alert('⚠ El archivo no tiene el formato correcto (versión 1 esperada).');
        return false;
      }
      if (!data.dynamics || typeof data.dynamics !== 'object') {
        alert('⚠ El archivo no contiene datos de usuario válidos.');
        return false;
      }
      localStorage.setItem(_lsKey(), JSON.stringify(data.dynamics));
      if (data.settings) {
        if (data.settings.theme) localStorage.setItem('aquelarre_theme', data.settings.theme);
        if (data.settings.cardSize) localStorage.setItem('aquelarre_card_size', data.settings.cardSize);
        if (data.settings.viewMode) localStorage.setItem('aquelarre_view_mode', data.settings.viewMode);
        if (data.settings.browseMode) localStorage.setItem('aquelarre_browse_mode', data.settings.browseMode);
        if (data.settings.showOcultos !== undefined) localStorage.setItem('aquelarre_show_ocultos', data.settings.showOcultos);
      }
      alert('✅ Datos restaurados correctamente. La página se recargará.');
      return true;
    } catch (e) {
      alert('⚠ Error al leer el archivo: ' + e.message);
      return false;
    }
  }

  function resetAllDynamics() {
    try { localStorage.removeItem(_lsKey()); } catch {}
    dynamics = {};
    merge();
  }

  function escapeHtml(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function escapeAttr(s) {
    if (!s) return '';
    return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/`/g, '&#96;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
  }

  let toastTimer = null;
  function showToast(msg) {
    let el = document.getElementById('toast-msg');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast-msg';
      el.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--bg-paper-dark);color:var(--ink);border:1px solid var(--gold);border-radius:var(--radius);padding:10px 20px;font-size:0.9em;z-index:999;opacity:0;transition:opacity 0.3s ease;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.style.opacity = '1';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.style.opacity = '0'; }, 2000);
  }

  function copyToClipboardWithFeedback(text, btn) {
    copyToClipboard(text);
    showToast('📁 Ruta copiada al portapapeles');
    const orig = btn.textContent;
    btn.textContent = '✓';
    btn.style.color = 'var(--green)';
    setTimeout(() => { btn.textContent = orig; btn.style.color = ''; }, 1500);
  }

  function renderStars(rating) {
    let h = '';
    for (let i = 1; i <= 5; i++) {
      h += `<span class="star${i <= rating ? ' active' : ''}" data-rating="${i}">${i <= rating ? '✦' : '✧'}</span>`;
    }
    return h;
  }

  return {
    init, getAll, getEntry, setRating, toggleFavorite, toggleRead, toggleOculto,
    markAsRead, setNotes, setTags, buildPdfPath, buildDirPath, updateEntry,
    setShowOcultos, getShowOcultos, isDirVisible,
    exportUserData, importUserData, resetAllDynamics,
    getLibraryName, getUrlBase, getFormatVersion, getLibraryId, getCatalogError,
    escapeHtml, escapeAttr, copyToClipboard, fallbackCopy, showToast, copyToClipboardWithFeedback, renderStars,
  };
})();
