const SETTINGS = (() => {
  const LS_THEME = 'aquelarre_theme';
  const LS_CARD_SIZE = 'aquelarre_card_size';

  function init() {
    loadTheme();
    loadCardSize();
    bindToggle();
    bindThemeRadios();
    bindCardSize();
    bindResets();
    bindClose();
    bindHelp();
    bindUserData();
  }

  function loadTheme() {
    const saved = localStorage.getItem(LS_THEME) || 'medieval';
    document.documentElement.setAttribute('data-theme', saved);
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(LS_THEME, theme);
  }

  function loadCardSize() {
    const size = localStorage.getItem(LS_CARD_SIZE) || 'normal';
    applyCardSize(size);
  }

  function setCardSize(size) {
    localStorage.setItem(LS_CARD_SIZE, size);
    applyCardSize(size);
  }

  function applyCardSize(size) {
    const min = size === 'small' ? '200px' : size === 'large' ? '360px' : '280px';
    document.documentElement.style.setProperty('--card-min', min);
  }

  function bindToggle() {
    const btn = document.getElementById('btn-config');
    const overlay = document.getElementById('settings-overlay');
    if (btn && overlay) {
      btn.addEventListener('click', () => overlay.classList.add('open'));
    }
  }

  function bindClose() {
    const overlay = document.getElementById('settings-overlay');
    const closeBtn = document.getElementById('settings-close');
    if (closeBtn && overlay) {
      closeBtn.addEventListener('click', () => overlay.classList.remove('open'));
      overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.classList.remove('open');
      });
    }
  }

  function bindHelp() {
    const btn = document.getElementById('btn-help');
    const overlay = document.getElementById('help-overlay');
    const closeBtn = document.getElementById('help-close');
    if (btn && overlay) {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        overlay.classList.add('open');
      });
      if (closeBtn) closeBtn.addEventListener('click', () => overlay.classList.remove('open'));
      overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.classList.remove('open');
      });
    }
  }

  function bindThemeRadios() {
    const radios = document.querySelectorAll('input[name="theme"]');
    const saved = localStorage.getItem(LS_THEME) || 'medieval';
    radios.forEach(r => {
      r.checked = r.value === saved;
      r.addEventListener('change', () => {
        if (r.checked) setTheme(r.value);
      });
    });
  }

  function bindCardSize() {
    const sel = document.getElementById('settings-card-size');
    if (!sel) return;
    const saved = localStorage.getItem(LS_CARD_SIZE) || 'normal';
    sel.value = saved;
    sel.addEventListener('change', () => {
      setCardSize(sel.value);
    });
  }

  function bindResets() {
    document.querySelectorAll('[data-reset]').forEach(btn => {
      btn.addEventListener('click', () => {
        const type = btn.dataset.reset;
        if (type === 'all') {
          if (!confirm('⚠ ¿Resetear TODOS los datos (favoritos, lecturas, valoraciones, notas)?')) return;
          if (!confirm('⚠ Esta acción NO se puede deshacer. ¿Continuar de todas formas?')) return;
          DATA.resetAllDynamics();
          APP.refresh();
          return;
        }
        const labels = { fav: 'favoritos', read: 'lecturas', rating: 'valoraciones', notes: 'notas' };
        const label = labels[type] || type;
        if (!confirm(`¿Resetear ${label}?`)) return;
        const allEntries = DATA.getAll();
        for (const entry of allEntries) {
          const updates = {};
          if (type === 'fav') updates.favorite = false;
          else if (type === 'read') { updates.read = false; updates.lastRead = null; }
          else if (type === 'rating') updates.rating = 0;
          else if (type === 'notes') updates.notes = '';
          DATA.updateEntry(entry.archivo_hash, updates);
        }
        APP.refresh();
      });
    });
  }

  function bindUserData() {
    const exportBtn = document.getElementById('export-user-data');
    const importBtn = document.getElementById('import-user-data');
    const fileInput = document.getElementById('import-file-input');

    if (exportBtn) {
      exportBtn.addEventListener('click', () => DATA.exportUserData());
    }
    if (importBtn && fileInput) {
      importBtn.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = ev => {
          if (DATA.importUserData(ev.target.result)) location.reload();
        };
        reader.readAsText(file);
        fileInput.value = '';
      });
    }
  }

  return { init };
})();
