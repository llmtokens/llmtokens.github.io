async function loadPrices() {
  const resp = await fetch('data/prices.latest.json');
  if (!resp.ok) {
    throw new Error(`Unable to load price data: ${resp.status}`);
  }
  return resp.json();
}

function renderTable(rows) {
  const tbody = document.querySelector('#prices-table tbody');
  tbody.innerHTML = '';

  rows.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.provider}</td>
      <td>${row.model}</td>
      <td>${row.usage_type}</td>
      <td>${row.unit}</td>
      <td>${row.price}</td>
      <td>${row.currency}</td>
      <td><a href="${row.source}" target="_blank" rel="noreferrer">Pricing</a></td>
    `;
    tbody.appendChild(tr);
  });
}

function setupFilters(rows) {
  const providerSelect = document.getElementById('provider-filter');
  const searchInput = document.getElementById('search-filter');

  const providers = Array.from(new Set(rows.map((r) => r.provider))).sort();
  providerSelect.innerHTML = `<option value="">All providers</option>` +
    providers.map((p) => `<option value="${p}">${p}</option>`).join('');

  const applyFilters = () => {
    const provider = providerSelect.value;
    const query = searchInput.value.toLowerCase();
    const filtered = rows.filter((row) => {
      const matchesProvider = provider ? row.provider === provider : true;
      const matchesQuery = row.model.toLowerCase().includes(query);
      return matchesProvider && matchesQuery;
    });
    renderTable(filtered);
  };

  providerSelect.addEventListener('change', applyFilters);
  searchInput.addEventListener('input', applyFilters);
  applyFilters();
}

loadPrices()
  .then((data) => {
    const rows = data.rows || [];
    renderTable(rows);
    setupFilters(rows);
  })
  .catch((err) => {
    const tbody = document.querySelector('#prices-table tbody');
    tbody.innerHTML = `<tr><td colspan="7">${err.message}</td></tr>`;
  });
