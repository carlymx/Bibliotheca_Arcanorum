const SEARCH = (() => {
  let currentQuery = '';
  let filters = { favorite: false, read: null, rating: 0, tipo: '', edicion: '' };
  let sortBy = 'title';
  let sortAsc = true;
  let callbacks = [];

  function init(inputEl, filterEls, sortSelect, sortDirBtn, onChange) {
    callbacks.push(onChange);

    inputEl.addEventListener('input', () => {
      currentQuery = inputEl.value;
      notify();
    });

    filterEls.forEach(el => {
      el.addEventListener('click', () => {
        const type = el.dataset.filter;
        el.classList.toggle('active');
        if (type === 'fav') filters.favorite = el.classList.contains('active');
        else if (type === 'read') {
          filters.read = el.classList.contains('active') ? true : null;
        }
        notify();
      });
    });

    if (sortSelect) {
      sortSelect.addEventListener('change', () => {
        sortBy = sortSelect.value;
        notify();
      });
    }

    if (sortDirBtn) {
      sortDirBtn.addEventListener('click', () => {
        sortAsc = !sortAsc;
        sortDirBtn.textContent = sortAsc ? '↑' : '↓';
        notify();
      });
    }

    const tipoSelect = document.getElementById('tipo-filter');
    if (tipoSelect) {
      tipoSelect.addEventListener('change', () => {
        filters.tipo = tipoSelect.value;
        notify();
      });
    }
  }

  function apply(entries) {
    let result = [...entries];

    if (currentQuery.trim()) {
      const q = currentQuery.toLowerCase().trim();
      result = result.filter(e =>
        (e.nombre_legible || '').toLowerCase().includes(q) ||
        (e.descripcion || '').toLowerCase().includes(q) ||
        (e.tipo || '').toLowerCase().includes(q) ||
        (e.edicion || '').toLowerCase().includes(q) ||
        (e.destino || '').toLowerCase().includes(q) ||
        (e.tags || []).some(t => t.toLowerCase().includes(q))
      );
    }

    if (filters.favorite) result = result.filter(e => e.favorite);
    if (filters.read === true) result = result.filter(e => e.read);
    if (filters.read === false) result = result.filter(e => !e.read);
    if (filters.rating > 0) result = result.filter(e => (e.rating || 0) >= filters.rating);
    if (filters.tipo) result = result.filter(e => (e.tipo || 'otro') === filters.tipo);
    if (filters.edicion) result = result.filter(e => e.edicion === filters.edicion);

    result.sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case 'title':
          cmp = (a.nombre_legible || '').localeCompare(b.nombre_legible || '');
          break;
        case 'rating':
          cmp = (b.rating || 0) - (a.rating || 0);
          break;
        case 'date':
          cmp = (b.addedDate || '').localeCompare(a.addedDate || '');
          break;
        case 'read':
          cmp = (b.lastRead || '').localeCompare(a.lastRead || '');
          break;
        default: cmp = 0;
      }
      return sortAsc ? cmp : -cmp;
    });

    return result;
  }

  function notify() {
    callbacks.forEach(cb => cb());
  }

  function updateTipoCounts() {
    const entries = DATA.getAll();
    const counts = {};
    entries.forEach(e => {
      const t = e.tipo || 'otro';
      counts[t] = (counts[t] || 0) + 1;
    });
    const select = document.getElementById('tipo-filter');
    if (!select) return;
    for (let i = 0; i < select.options.length; i++) {
      const opt = select.options[i];
      if (!opt.value) { opt.textContent = 'Todos'; continue; }
      const label = opt.dataset.label || opt.value;
      opt.textContent = `${label} (${counts[opt.value] || 0})`;
    }
  }

  function getQuery() { return currentQuery; }
  function getFilters() { return { ...filters }; }
  function getSort() { return { sortBy, sortAsc }; }

  return { init, apply, updateTipoCounts, getQuery, getFilters, getSort };
})();
