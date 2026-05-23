const TREE = (() => {
  let onSelectCallback = null;

  function isPathVisible(pathParts) {
    if (typeof DATA === 'undefined' || !DATA.isDirVisible) return true;
    const path = pathParts.join('/');
    return DATA.isDirVisible(path);
  }

  function build(entries) {
    const root = { name: '📁 Raíz', children: {}, count: 0 };
    for (const e of entries) {
      const dest = e.destino || '';
      const parts = dest.split('/').filter(Boolean);
      if (!isPathVisible(parts)) continue;
      let node = root;
      for (const part of parts) {
        if (!node.children[part]) {
          node.children[part] = { name: part, children: {}, count: 0 };
        }
        node = node.children[part];
      }
      node.count++;
    }
    return root;
  }

  function render(node, container, depth = 0, filterText = '') {
    const keys = Object.keys(node.children);
    if (depth === 0 && keys.length === 0) {
      container.innerHTML = '<div class="tree-item" style="color:#8a7a6a;font-style:italic;padding:10px 14px;">Sin categorías</div>';
      return;
    }
    const sorted = keys.sort((a, b) => {
      const aNum = parseInt(a), bNum = parseInt(b);
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      return a.localeCompare(b);
    });
    let html = '';
    if (depth === 0) {
      const grandTotal = countAll(node);
      html += `<div class="tree-item root-item" data-path="" data-depth="0" style="padding-left:14px">
        <span class="tree-arrow open">▶</span> <span class="icon">📁</span> Todos los manuscritos <span class="count">${grandTotal}</span>
      </div>
      <div class="tree-children" data-parent="">`;
    }
    for (const key of sorted) {
      const child = node.children[key];
      const total = countAll(child);
      if (filterText && !key.toLowerCase().includes(filterText.toLowerCase()) && total === 0) continue;
      const hasChildren = Object.keys(child.children).length > 0;
      const arrow = hasChildren ? '<span class="tree-arrow">▶</span>' : '<span style="width:0.7em;display:inline-block;"></span>';
      const label = key.replace(/^\d+\s*-\s*/, '');
      html += `<div class="tree-item" data-path="${key}" data-depth="${depth + 1}" style="padding-left:${14 + (depth + 1) * 16}px">
        ${arrow} <span class="icon">${getIcon(key)}</span> ${escapeHtml(label)} <span class="count">${total}</span>
      </div>`;
      if (hasChildren) {
        html += `<div class="tree-children collapsed" data-parent="${key}">`;
        html += renderNode(child, container, depth + 1, filterText, key);
        html += `</div>`;
      }
    }
    if (depth === 0) {
      html += `</div>`;
    }
    return html;
  }

  function renderNode(node, container, depth, filterText, parentKey) {
    const keys = Object.keys(node.children);
    if (keys.length === 0) return '';
    const sorted = keys.sort((a, b) => {
      const aNum = parseInt(a), bNum = parseInt(b);
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      return a.localeCompare(b);
    });
    let html = '';
    for (const key of sorted) {
      const child = node.children[key];
      const total = countAll(child);
      if (filterText && !key.toLowerCase().includes(filterText.toLowerCase()) && total === 0) continue;
      const hasChildren = Object.keys(child.children).length > 0;
      const arrow = hasChildren ? '<span class="tree-arrow">▶</span>' : '<span style="width:0.7em;display:inline-block;"></span>';
      const label = key.replace(/^\d+\s*-\s*/, '');
      html += `<div class="tree-item" data-path="${parentKey}/${key}" data-depth="${depth}" style="padding-left:${14 + depth * 16}px">
        ${arrow} <span class="icon">${getIcon(key)}</span> ${escapeHtml(label)} <span class="count">${total}</span>
      </div>`;
      if (hasChildren) {
        html += `<div class="tree-children collapsed" data-parent="${key}">`;
        html += renderNode(child, container, depth + 1, filterText, `${parentKey}/${key}`);
        html += `</div>`;
      }
    }
    return html;
  }

  function countAll(node) {
    let total = node.count || 0;
    for (const k in node.children) {
      total += countAll(node.children[k]);
    }
    return total;
  }

  function getIcon(name) {
    if (/manual/i.test(name)) return '📖';
    if (/expansio/i.test(name)) return '⚔';
    if (/modulo|aventura/i.test(name)) return '🗺';
    if (/suplemento/i.test(name)) return '📜';
    if (/mapa/i.test(name)) return '🌍';
    if (/documentaci/i.test(name)) return '📄';
    if (/no clasif/i.test(name)) return '❓';
    if (/ia/i.test(name)) return '🤖';
    if (/otro/i.test(name)) return '📦';
    if (/edici/i.test(name)) return '📚';
    return '📁';
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  let _bound = false;
  function setupEventListeners(container, onSelect) {
    onSelectCallback = onSelect;
    if (_bound) return;
    _bound = true;
    container.addEventListener('click', e => {
      const item = e.target.closest('.tree-item');
      if (!item) return;
      const path = item.dataset.path;
      const arrow = item.querySelector('.tree-arrow');
      if (arrow) {
        const childrenDiv = item.nextElementSibling;
        if (childrenDiv && childrenDiv.classList.contains('tree-children')) {
          const isOpen = arrow.classList.toggle('open');
          childrenDiv.classList.toggle('collapsed', !isOpen);
        }
      }
      if (onSelectCallback) {
        container.querySelectorAll('.tree-item.active').forEach(el => el.classList.remove('active'));
        item.classList.add('active');
        onSelectCallback(path);
      }
    });
  }

  function filter(container, text) {
    container.querySelectorAll('.tree-item').forEach(el => {
      const match = !text || el.textContent.toLowerCase().includes(text.toLowerCase());
      el.style.display = match ? '' : 'none';
    });
    container.querySelectorAll('.tree-children').forEach(el => {
      const hasVisible = Array.from(el.querySelectorAll(':scope > .tree-item')).some(i => i.style.display !== 'none');
      el.style.display = hasVisible ? '' : 'none';
    });
  }

  return { build, render, setupEventListeners, filter, getIcon };
})();
