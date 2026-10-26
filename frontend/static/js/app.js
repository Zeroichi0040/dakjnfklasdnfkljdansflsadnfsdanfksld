import {
  api
} from './api-client.js';
document.documentElement.classList.add('js');

const menu = document.querySelector('.menu-toggle');
const sidebar = document.querySelector('#sidebar');
if (menu && sidebar) {
  const smallScreen = window.matchMedia('(max-width:800px)');
  const setMenu = (open, restoreFocus = false) => {
    const expanded = smallScreen.matches && open;
    menu.setAttribute('aria-expanded', String(expanded));
    sidebar.classList.toggle('is-open', expanded);
    sidebar.inert = smallScreen.matches && !expanded;
    if (sidebar.inert) sidebar.setAttribute('aria-hidden', 'true');
    else sidebar.removeAttribute('aria-hidden');
    if (expanded) sidebar.querySelector('button, a')?.focus();
    else if (restoreFocus) menu.focus();
  };
  setMenu(false);
  menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
  sidebar.querySelector('.sidebar-close')?.addEventListener('click', () => setMenu(false, true));
  smallScreen.addEventListener('change', () => setMenu(false));
  document.addEventListener('click', event => {
    if (!sidebar.contains(event.target) && !menu.contains(event.target)) setMenu(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') setMenu(false, true);
  });
}

document.addEventListener('submit', event => {
  if (event.target.dataset.confirm && !window.confirm(event.target.dataset.confirm)) event.preventDefault();
});

/* Read current rows through the same resource's JSON endpoint. No HTML injection. */
for (const panel of document.querySelectorAll('[data-resource-list]')) {
  const refresh = panel.querySelector('[data-refresh]');
  refresh?.addEventListener('click', async () => {
    const status = panel.querySelector('[data-refresh-status]');
    refresh.disabled = true;
    status.textContent = 'Loading current records…';
    try {
      const result = await api(panel.dataset.apiUrl);
      const columns = [...panel.querySelectorAll('th[data-field]')].map(th => th.dataset.field);
      const rows = [];
      for (const record of result.data) {
        const row = document.createElement('tr');
        columns.forEach((name, index) => {
          const cell = document.createElement('td');
          const value = record[name] === true ? 'Yes' : record[name] === false ? 'No' : record[name] ?? '—';
          const text = String(value).slice(0, 100);
          if (index === 0) {
            const link = document.createElement('a');
            link.className = 'record-link';
            link.href = `${panel.dataset.recordBase}/${record.id}`;
            link.textContent = text;
            cell.append(link);
          } else cell.textContent = text;
          row.append(cell);
        });
        const updated = document.createElement('td');
        updated.textContent = new Date(record.updated_at).toLocaleDateString();
        const actions = document.createElement('td');
        const edit = document.createElement('a');
        edit.href = `${panel.dataset.recordBase}/${record.id}/edit`;
        edit.textContent = 'Edit';
        actions.append(edit);
        row.append(updated, actions);
        rows.push(row);
      }
      if (!rows.length) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = columns.length + 2;
        cell.textContent = 'No matching records. Add one or change your search.';
        row.append(cell);
        rows.push(row);
      }
      panel.querySelector('tbody').replaceChildren(...rows);
      panel.querySelector('[data-record-count]').textContent = `${result.pagination.total} records`;
      status.textContent = 'Updated from the server.';
    } catch (error) {
      status.textContent = error.message;
    } finally {
      refresh.disabled = false;
    }
  });
}
