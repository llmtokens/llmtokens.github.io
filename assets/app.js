const priceUrl = 'data/prices.latest.json';
const diffUrl = 'data/diffs/latest.json';

const statusEl = document.getElementById('data-status');
const lastUpdatedEl = document.getElementById('last-updated');
const changesBody = document.getElementById('changes-body');
const changesUpdatedEl = document.getElementById('changes-updated');

async function fetchJson(url, friendlyName) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`${friendlyName} failed to load (${resp.status})`);
  }
  return resp.json();
}

function formatTimestamp(isoString) {
  if (!isoString) return '--';
  const dt = new Date(isoString);
  return dt.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function formatPrice(value, currency) {
  if (typeof value !== 'number') return value;
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: value < 1 ? 4 : 2,
      maximumFractionDigits: 6,
    }).format(value);
  } catch (err) {
    return `${value} ${currency || ''}`.trim();
  }
}

function initDropdown(select, placeholder, options) {
  select.innerHTML = '';
  const defaultOpt = document.createElement('option');
  defaultOpt.value = '';
  defaultOpt.textContent = placeholder;
  select.appendChild(defaultOpt);

  options.forEach((opt) => {
    const el = document.createElement('option');
    el.value = opt;
    el.textContent = opt;
    select.appendChild(el);
  });
}

function renderChanges(diffData, errorMessage = '') {
  if (changesUpdatedEl) {
    changesUpdatedEl.textContent = diffData?.generated_at
      ? `Diff generated: ${formatTimestamp(diffData.generated_at)}`
      : '';
  }

  if (errorMessage) {
    changesBody.innerHTML = `<p class="muted">Change log unavailable: ${errorMessage}</p>`;
    return;
  }

  if (!diffData || (!diffData.added?.length && !diffData.updated?.length && !diffData.removed?.length)) {
    changesBody.innerHTML = '<p class="muted">No changes recorded for the last run.</p>';
    return;
  }

  const fragments = [];

  const renderGroup = (items, label) => {
    if (!items?.length) return;
    const list = document.createElement('ul');
    list.className = 'change-list';

    items.forEach((item) => {
      const li = document.createElement('li');
      const parts = [
        `<strong>${item.provider}</strong>`,
        item.model,
        item.usage_type ? `(${item.usage_type})` : '',
      ].filter(Boolean);

      if (typeof item.old_price === 'number' && typeof item.new_price === 'number') {
        const oldVal = formatPrice(item.old_price, item.currency);
        const newVal = formatPrice(item.new_price, item.currency);
        parts.push(`changed from ${oldVal} to ${newVal}`);
      } else if (typeof item.price === 'number') {
        parts.push(`price ${formatPrice(item.price, item.currency)}`);
      }
      if (item.unit) parts.push(`per ${item.unit}`);
      if (item.source) {
        parts.push(`<a href="${item.source}" target="_blank" rel="noreferrer">source</a>`);
      }

      li.innerHTML = parts.join(' ');
      list.appendChild(li);
    });

    const group = document.createElement('div');
    group.className = 'change-group';
    group.innerHTML = `<h3>${label}</h3>`;
    group.appendChild(list);
    fragments.push(group);
  };

  renderGroup(diffData.added, 'Added');
  renderGroup(diffData.updated, 'Updated');
  renderGroup(diffData.removed, 'Removed');

  changesBody.innerHTML = '';
  fragments.forEach((el) => changesBody.appendChild(el));
}

function buildTabulator(rows) {
  const table = new Tabulator('#prices-table', {
    data: rows,
    layout: 'fitColumns',
    placeholder: 'No pricing data available',
    height: '650px',
    columns: [
      { title: 'Provider', field: 'provider', width: 140 },
      { title: 'Model', field: 'model', minWidth: 200 },
      {
        title: 'Usage',
        field: 'usage_type',
        width: 120,
        formatter: (cell) => {
          const val = cell.getValue();
          return val ? val.charAt(0).toUpperCase() + val.slice(1) : '';
        },
      },
      { title: 'Unit', field: 'unit', width: 140 },
      {
        title: 'Price',
        field: 'price',
        hozAlign: 'right',
        width: 140,
        formatter: (cell) => formatPrice(cell.getValue(), cell.getRow().getData().currency),
      },
      { title: 'Currency', field: 'currency', width: 100 },
      {
        title: 'Source',
        field: 'source',
        headerSort: false,
        width: 120,
        formatter: (cell) => {
          const url = cell.getValue();
          return url ? `<a href="${url}" target="_blank" rel="noreferrer">Pricing</a>` : '';
        },
      },
    ],
  });

  return table;
}

function setupFilters(table, rows) {
  const providerSelect = document.getElementById('provider-filter');
  const modelSelect = document.getElementById('model-filter');
  const usageSelect = document.getElementById('usage-filter');
  const searchInput = document.getElementById('search-filter');

  const providers = Array.from(new Set(rows.map((r) => r.provider))).sort();
  const models = Array.from(new Set(rows.map((r) => r.model))).sort();

  initDropdown(providerSelect, 'All providers', providers);
  initDropdown(modelSelect, 'All models', models);

  const filterState = {
    provider: '',
    model: '',
    usage: '',
    search: '',
  };

  const applyFilters = () => {
    table.setFilter((data) => {
      if (filterState.provider && data.provider !== filterState.provider) return false;
      if (filterState.model && data.model !== filterState.model) return false;
      if (filterState.usage && data.usage_type !== filterState.usage) return false;

      if (filterState.search) {
        const term = filterState.search;
        const haystack = `${data.provider} ${data.model} ${data.unit} ${data.usage_type}`.toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  };

  providerSelect.addEventListener('change', (e) => {
    filterState.provider = e.target.value;
    applyFilters();
  });

  modelSelect.addEventListener('change', (e) => {
    filterState.model = e.target.value;
    applyFilters();
  });

  usageSelect.addEventListener('change', (e) => {
    filterState.usage = e.target.value;
    applyFilters();
  });

  searchInput.addEventListener('input', (e) => {
    filterState.search = e.target.value.toLowerCase();
    applyFilters();
  });
}

async function bootstrap() {
  try {
    statusEl.textContent = 'Loading data…';

    let diffError = '';
    const diffPromise = fetchJson(diffUrl, 'Diff data').catch((err) => {
      console.warn(err);
      diffError = err.message;
      return null;
    });

    const [priceData, diffData] = await Promise.all([
      fetchJson(priceUrl, 'Pricing data'),
      diffPromise,
    ]);

    const rows = priceData?.rows || [];
    const table = buildTabulator(rows);
    setupFilters(table, rows);

    lastUpdatedEl.textContent = `Last updated: ${formatTimestamp(priceData?.generated_at)}`;
    statusEl.textContent = `${rows.length} rows loaded`;

    renderChanges(diffData, diffError);
  } catch (err) {
    statusEl.textContent = err.message;
    lastUpdatedEl.textContent = 'Last updated: --';
  }
}

document.addEventListener('DOMContentLoaded', bootstrap);
