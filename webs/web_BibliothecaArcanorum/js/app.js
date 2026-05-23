const APP = (() => {
  let allEntries = [];
  let currentBrowsePath = '';

  function init() {
    allEntries = DATA.init();
    CARD.init({
      onDetail: (hash) => DETAIL.open(hash),
      onFolderClick: (path) => navigateToFolder(path),
    });
    DETAIL.init();
    SETTINGS.init();
    renderSplash();
  }

  function renderSplash() {
    const splash = document.getElementById('splash');
    const ornament = splash.querySelector('.splash-ornament');
    const enterBtn = splash.querySelector('.btn-enter');
    const errorBox = document.getElementById('splash-error');
    const count = allEntries.length;
    const catalogErr = DATA.getCatalogError();

    const libName = DATA.getLibraryName();
    const name = libName || 'Biblioteca de Documentos';
    const titleEl = document.getElementById('splash-title');
    if (titleEl) titleEl.textContent = name.toUpperCase();

    if (catalogErr) {
      errorBox.style.display = 'block';
      enterBtn.style.display = 'none';
      return;
    }

    ornament.textContent = `«${count} manuscritos catalogados»`;
    enterBtn.addEventListener('click', () => {
      splash.classList.add('hidden');
      document.getElementById('app').classList.add('active');
      initLibrary();
    });
  }

  function initLibrary() {
    CARD.render(allEntries, document.getElementById('card-grid'));
    refresh();
    initSearch();
    SEARCH.updateTipoCounts();

    const libName = DATA.getLibraryName();
    const name = libName || 'Biblioteca de Documentos';
    const libTitleEl = document.getElementById('library-name');
    if (libTitleEl) libTitleEl.textContent = name;

    const helpTitleEl = document.getElementById('help-title');
    if (helpTitleEl) helpTitleEl.textContent = name;

    document.title = name;
    initTabs();
    initBrowseToggle();
    initTreeToggle();
    initViewToggle();
    initOcultosToggle();
    SETTINGS.bindUI();
  }

  function initOcultosToggle() {
    const btn = document.getElementById('btn-toggle-ocultos');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const show = !DATA.getShowOcultos();
      DATA.setShowOcultos(show);
      btn.classList.toggle('active', show);
      refresh();
    });
    if (DATA.getShowOcultos()) {
      btn.classList.add('active');
    }
  }

  function renderTree(entries) {
    const container = document.getElementById('tree-container');
    if (!container) return;
    const treeData = TREE.build(entries);
    container.innerHTML = TREE.render(treeData, container);
    TREE.setupEventListeners(container, path => {
      currentBrowsePath = path || '';
      if (CARD.getBrowseMode() === 'folder') {
        renderFolderView(currentBrowsePath);
      } else {
        const filtered = path
          ? allEntries.filter(e => e.destino && e.destino.startsWith(path))
          : allEntries;
        renderCards(filtered);
        renderStats(filtered);
      }
    });
  }

  function renderCards(entries) {
    const container = document.getElementById('card-grid');
    if (!container) return;
    const filtered = SEARCH.apply(entries);
    CARD.render(filtered, container);
    updateDetailPanel();
  }

  function renderStats(entries) {
    const bar = document.getElementById('stats-bar');
    if (!bar) return;
    const filtered = SEARCH.apply(entries);
    const total = entries.length;
    const shown = filtered.length;
    const withCover = entries.filter(e => e.portada).length;
    const read = entries.filter(e => e.read).length;
    const fav = entries.filter(e => e.favorite).length;
    const avgRating = entries.filter(e => e.rating > 0).reduce((s, e) => s + e.rating, 0);
    const raters = entries.filter(e => e.rating > 0).length;
    bar.innerHTML = `
      <span>📚 ${shown}/${total} archivos</span>
      <span>🖼 ${withCover} portadas</span>
      <span>✓ ${read} leídos</span>
      <span>★ ${fav} favoritos</span>
      <span>⭐ ${raters ? (avgRating / raters).toFixed(1) : '—'} media</span>
    `;
  }

  function renderFolderView(path) {
    const container = document.getElementById('card-grid');
    if (!container) return;
    const treeData = TREE.build(allEntries);
    const node = findTreeNode(treeData, path);
    if (!node) {
      container.className = 'card-grid empty';
      container.innerHTML = '<span>📁 Categoría no encontrada</span>';
      return;
    }
    const childKeys = Object.keys(node.children).sort((a, b) => {
      const aN = parseInt(a), bN = parseInt(b);
      if (!isNaN(aN) && !isNaN(bN)) return aN - bN;
      return a.localeCompare(b);
    });
    const folders = [];
    for (const key of childKeys) {
      const child = node.children[key];
      const label = key.replace(/^\d+\s*-\s*/, '');
      const childPath = path ? `${path}/${key}` : key;
      const total = countAllEntries(child);
      const icon = TREE.getIcon ? TREE.getIcon(key) : '📁';
      folders.push({ path: childPath, label, count: total, icon, depth: path.split('/').filter(Boolean).length + 1 });
    }
    const normalizedPath = path ? (path.endsWith('/') ? path : path + '/') : '';
    const directEntries = allEntries.filter(e => e.destino === normalizedPath || e.destino === path);
    const filtered = SEARCH.apply(directEntries);
    if (folders.length === 0 && filtered.length === 0) {
      container.className = 'card-grid empty';
      container.innerHTML = '<span>📁 Esta categoría está vacía</span>';
      return;
    }
    CARD.renderWithFolders(folders, filtered, container);
    renderStats(directEntries.length > 0 ? directEntries : allEntries.filter(e => e.destino && e.destino.startsWith(normalizedPath)));
  }

  function navigateToFolder(path) {
    currentBrowsePath = path;
    const container = document.getElementById('tree-container');
    if (container) {
      const items = container.querySelectorAll('.tree-item');
      items.forEach(el => {
        const match = el.dataset.path === path || (path === '' && el.dataset.path === '');
        el.classList.toggle('active', match);
        if (match) {
          let parent = el.parentElement;
          while (parent && parent.classList.contains('tree-children')) {
            parent.classList.remove('collapsed');
            const arrow = parent.previousElementSibling?.querySelector('.tree-arrow');
            if (arrow) arrow.classList.add('open');
            parent = parent.parentElement;
          }
        }
      });
    }
    renderFolderView(path);
  }

  function findTreeNode(node, path) {
    if (!path) return node;
    const parts = path.split('/').filter(Boolean);
    let current = node;
    for (const part of parts) {
      if (current.children && current.children[part]) {
        current = current.children[part];
      } else {
        return null;
      }
    }
    return current;
  }

  function countAllEntries(node) {
    let total = node.count || 0;
    for (const k in node.children) {
      total += countAllEntries(node.children[k]);
    }
    return total;
  }

  function initSearch() {
    const input = document.getElementById('search-input');
    const filterEls = document.querySelectorAll('[data-filter]');
    const sortSelect = document.getElementById('sort-select');
    const sortDir = document.getElementById('sort-dir');
    const clearBtn = document.getElementById('search-clear');

    SEARCH.init(input, filterEls, sortSelect, sortDir, () => {
      refreshView();
    });

    if (clearBtn) {
      input.addEventListener('input', () => {
        clearBtn.classList.toggle('visible', !!input.value);
      });
      clearBtn.addEventListener('click', () => {
        input.value = '';
        clearBtn.classList.remove('visible');
        input.dispatchEvent(new Event('input'));
        input.focus();
      });
    }
  }

  function refreshView() {
    if (CARD.getBrowseMode() === 'folder' && currentBrowsePath !== undefined) {
      renderFolderView(currentBrowsePath);
    } else {
      renderCards(allEntries);
    }
    renderStats(allEntries);
    TREE.filter(document.getElementById('tree-container'), SEARCH.getQuery());
  }

  function refresh() {
    allEntries = DATA.getAll();
    refreshView();
    renderTree(allEntries);
    renderStats(allEntries);
  }

  function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const view = tab.dataset.view;


        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        const libraryView = document.getElementById('library-view');
        const rolmastersView = document.getElementById('rolmasters-view');
        const ayudaView = document.getElementById('ayuda-view');

        if (view === 'ayuda') {
          libraryView.style.display = 'none';
          rolmastersView.style.display = 'none';
          ayudaView.style.display = 'block';
          return;
        }

        if (view === 'rolmasters') {
          libraryView.style.display = 'none';
          rolmastersView.style.display = 'block';
          ayudaView.style.display = 'none';
          const iframe = rolmastersView.querySelector('iframe');
          iframe.src = '../web_rolmasters/rolmasters.html';
          return;
        }

        libraryView.style.display = '';
        rolmastersView.style.display = 'none';
        ayudaView.style.display = 'none';

        if (view === 'biblioteca') {
          refresh();
          return;
        }

        const dirMap = {
          manuales: '01',
          expansiones: '02',
          modulos: '03',
          suplementos: '05',
          mapas: '80',
        };
        const prefix = dirMap[view];
        if (prefix) {
          currentBrowsePath = prefix;
          const prefixEntries = allEntries.filter(e => e.destino && e.destino.startsWith(prefix));
          if (CARD.getBrowseMode() === 'folder') {
            renderFolderView(prefix);
          } else {
            renderCards(prefixEntries);
          }
          renderStats(prefixEntries);
        }
      });
    });

  }

  function initBrowseToggle() {
    const btn = document.getElementById('browse-toggle');
    if (!btn) return;
    const mode = CARD.getBrowseMode();
    btn.textContent = mode === 'folder' ? '📄' : '📂';
    btn.title = mode === 'folder' ? 'Modo plano' : 'Modo carpetas';
    btn.addEventListener('click', () => {
      const next = CARD.getBrowseMode() === 'flat' ? 'folder' : 'flat';
      CARD.setBrowseMode(next);
      btn.textContent = next === 'folder' ? '📄' : '📂';
      btn.title = next === 'folder' ? 'Modo plano' : 'Modo carpetas';
      if (next === 'folder') {
        renderFolderView(currentBrowsePath);
      } else {
        const filtered = currentBrowsePath
          ? allEntries.filter(e => e.destino && e.destino.startsWith(currentBrowsePath))
          : allEntries;
        renderCards(filtered);
        renderStats(filtered);
      }
    });
  }

  function initTreeToggle() {
    const btn = document.getElementById('tree-toggle');
    const sidebar = document.querySelector('.tree-sidebar');
    const overlay = document.getElementById('mobile-menu-overlay');
    if (btn && sidebar && overlay) {
      btn.addEventListener('click', () => {
        sidebar.classList.toggle('mobile-open');
        overlay.classList.toggle('open');
      });
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('open');
      });
    }
  }

  function initViewToggle() {
    const btn = document.getElementById('view-toggle');
    if (!btn) return;
    btn.textContent = CARD.getViewMode() === 'list' ? '⊞' : '☷';
    btn.addEventListener('click', () => {
      const next = CARD.getViewMode() === 'grid' ? 'list' : 'grid';
      CARD.setViewMode(next);
      btn.textContent = next === 'list' ? '⊞' : '☷';
      refreshView();
    });
  }

  function updateDetailPanel() {
    DETAIL.refresh();
  }

  init();

  return { refresh };
})();
