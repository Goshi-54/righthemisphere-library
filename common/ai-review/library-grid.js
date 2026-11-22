(() => {
  const base = new URL('./', document.currentScript.src);
  let catalog;
  const selected = new Set();
  let initialSelection = new URLSearchParams(location.search).get('compare');
  const settings = { query: '', group: '', state: '', onlySelected: false,
    animate: !matchMedia('(prefers-reduced-motion: reduce)').matches };
  function loadCatalog() {
    // Use the same published records and representative frames as the detailed review.
    if (!catalog) catalog = fetch(new URL('index.html', base)).then(async response => {
      if (!response.ok) throw new Error('catalog unavailable');
      const template = document.createElement('template');
      template.innerHTML = await response.text();
      return JSON.parse(template.content.querySelector('script#assets').textContent);
    }).catch(error => { catalog = undefined; throw error; });
    return catalog;
  }
  function element(tag, text, cls) {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }
  function button(text, action) {
    const node = element('button', text, 'small-btn');
    node.type = 'button';
    node.addEventListener('click', action);
    return node;
  }
  function dropdown(label, choices, value, change) {
    const select = element('select');
    select.setAttribute('aria-label', label);
    for (const [text, key] of choices) select.add(new Option(text, key));
    select.value = value;
    select.addEventListener('change', () => change(select.value));
    return select;
  }
  function stateLabel(row) {
    return row.state.includes('正式') ? '正式掲載' : row.state;
  }
  class LibraryGrid extends HTMLElement {
    async connectedCallback() {
      this.textContent = '制作物を読み込み中…';
      try {
        const rows = await loadCatalog();
        if (!this.isConnected) return;
        if (initialSelection) {
          const ids = new Set(initialSelection.split(','));
          for (const row of rows) if (ids.has(row.id)) selected.add(row.id);
          settings.onlySelected = selected.size > 0;
          initialSelection = '';
        }
        this.show(rows);
      } catch {
        if (this.isConnected) this.replaceChildren('制作物を読み込めませんでした。', button('再読み込み', () => this.connectedCallback()));
      }
    }
    show(rows) {
      const controls = element('div', null, 'cc-controls');
      const search = element('input');
      search.type = 'search';
      search.placeholder = '素材名・IDを検索';
      search.setAttribute('aria-label', search.placeholder);
      search.value = settings.query;
      const choices = (label, values) => [[label, ''], ...Array.from(new Set(values), value => [value, value])];
      const groups = dropdown('制作グループ', choices('すべての制作グループ', rows.map(r => r.group)), settings.group, value => {
        settings.group = value; resetList();
      });
      const states = dropdown('掲載状況', choices('すべての掲載状況', rows.map(stateLabel)), settings.state, value => {
        settings.state = value; resetList();
      });
      const toggle = button('', () => { settings.onlySelected = !settings.onlySelected; resetList(); });
      const play = button('', () => { settings.animate = !settings.animate; render(); });
      const count = element('span', '', 'cc-count');
      count.setAttribute('role', 'status');
      const grid = element('div', null, 'icon-grid cc-gallery');
      const more = button('さらに表示', () => { limit += 36; render(); });
      const limitStart = 36;
      let limit = limitStart;
      const resetList = () => { limit = limitStart; render(); };
      search.addEventListener('input', () => { settings.query = search.value; resetList(); });
      controls.append(search, groups, states, toggle, play);
      this.replaceChildren(controls, count, grid, more);
      function syncButtons() {
        toggle.textContent = settings.onlySelected ? 'すべての素材に戻る' : '選んだ素材を並べる（' + selected.size + '）';
        toggle.disabled = !selected.size && !settings.onlySelected;
        toggle.setAttribute('aria-pressed', String(settings.onlySelected));
        play.textContent = settings.animate ? '静止画で見る' : '動きを見る';
        play.setAttribute('aria-pressed', String(settings.animate));
      }
      function card(row) {
        const node = element('article', null, 'icon-card pixel cc-sprite');
        node.dataset.asset = row.id;
        const img = element('img');
        img.loading = 'lazy'; img.decoding = 'async'; img.alt = row.title;
        img.src = settings.animate || row.frames === 1 ? new URL(row.media, base).href : row.poster;
        const title = element('strong', row.title);
        const info = element('small', row.id + ' · ' + stateLabel(row), 'cc-info');
        const label = element('label', null, 'cc-pick');
        const input = element('input'); input.type = 'checkbox';
        input.checked = selected.has(row.id);
        input.setAttribute('aria-label', row.title + 'を比較に選ぶ');
        input.addEventListener('change', () => {
          if (input.checked) selected.add(row.id); else selected.delete(row.id);
          if (settings.onlySelected) {
            if (!selected.size) settings.onlySelected = false;
            render();
          } else syncButtons();
        });
        label.append(input, '比較に選ぶ');
        const details = element('details');
        details.append(element('summary', '評価・原寸・各版'));
        const primary = element('a', '原寸を開く');
        primary.href = new URL(row.media, base).href; primary.target = '_blank'; primary.rel = 'noopener';
        details.append(element('p', row.note), primary);
        for (const [caption, url] of row.links) {
          const link = element('a', caption); link.href = new URL(url, base).href;
          link.target = '_blank'; link.rel = 'noopener'; details.append(link);
        }
        node.append(img, title, info, label, details);
        return node;
      }
      function render() {
        const query = settings.query.trim().normalize('NFKC').toLowerCase();
        const visible = rows.filter(row => settings.onlySelected ? selected.has(row.id) :
          (!settings.group || row.group === settings.group) && (!settings.state || stateLabel(row) === settings.state) &&
          (!query || [row.id,row.title,row.group].join(' ').normalize('NFKC').toLowerCase().includes(query)));
        for (const control of [search, groups, states]) control.disabled = settings.onlySelected;
        const shown = settings.onlySelected ? visible : visible.slice(0, limit);
        grid.replaceChildren(...shown.map(card));
        count.textContent = visible.length ? shown.length + ' / ' + visible.length + '件' : '該当する素材はありません';
        more.hidden = shown.length >= visible.length;
        syncButtons();
      }
      render();
    }
  }
  customElements.define('cc-library-grid', LibraryGrid);
})();
