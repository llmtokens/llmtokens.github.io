const pricingTableElement = document.getElementById("pricing-table");
const searchInput = document.getElementById("searchInput");
const modelFilter = document.getElementById("modelFilter");
const conditionFilter = document.getElementById("conditionFilter");
const lastUpdatedEl = document.getElementById("lastUpdated");
const changesList = document.getElementById("changesList");
const changesEmpty = document.getElementById("changesEmpty");
const changesTimestamp = document.getElementById("changesTimestamp");

let table;
let pricingData = [];

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const numberValue = Number(value);
  return `$${numberValue.toFixed(4)}`;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function linkFormatter(cell) {
  const url = cell.getValue();
  if (!url) return "—";
  return `<a href="${url}" target="_blank" rel="noreferrer noopener">Source</a>`;
}

function buildFilters() {
  const models = new Set();
  const conditions = new Set();

  pricingData.forEach((item) => {
    models.add(item.model);
    if (item.condition) conditions.add(item.condition);
  });

  [modelFilter, conditionFilter].forEach((select) => {
    while (select.options.length > 1) {
      select.remove(1);
    }
  });

  [...models].sort().forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    modelFilter.append(option);
  });

  [...conditions].sort().forEach((condition) => {
    const option = document.createElement("option");
    option.value = condition;
    option.textContent = condition;
    conditionFilter.append(option);
  });
}

function applyFilters() {
  const query = searchInput.value.trim().toLowerCase();
  const modelSelection = modelFilter.value;
  const conditionSelection = conditionFilter.value;

  const filters = [];

  if (query) {
    filters.push((data) =>
      [data.provider, data.model, data.notes]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }

  if (modelSelection !== "all") {
    filters.push((data) => data.model === modelSelection);
  }

  if (conditionSelection !== "all") {
    filters.push((data) => data.condition === conditionSelection);
  }

  if (!filters.length) {
    table.clearFilter();
    return;
  }

  table.setFilter((data) => filters.every((fn) => fn(data)));
}

function renderTable() {
  table = new Tabulator(pricingTableElement, {
    data: pricingData,
    layout: "fitColumns",
    height: 520,
    placeholder: "No pricing data found.",
    columns: [
      { title: "Provider", field: "provider", width: 140 },
      { title: "Model", field: "model", width: 180 },
      { title: "Condition", field: "condition", width: 120 },
      {
        title: "Input Price",
        field: "input",
        formatter: (cell) => `${formatCurrency(cell.getValue())}`,
        hozAlign: "right",
      },
      {
        title: "Output Price",
        field: "output",
        formatter: (cell) => `${formatCurrency(cell.getValue())}`,
        hozAlign: "right",
      },
      { title: "Unit", field: "unit", width: 130 },
      { title: "Notes", field: "notes", widthGrow: 1 },
      { title: "Last Updated", field: "updated", formatter: (cell) => formatDate(cell.getValue()) },
      { title: "Source", field: "source", formatter: linkFormatter, width: 100 },
    ],
  });

  searchInput.addEventListener("input", applyFilters);
  modelFilter.addEventListener("change", applyFilters);
  conditionFilter.addEventListener("change", applyFilters);
}

function updateLastUpdated(timestamp) {
  if (!timestamp) return;
  lastUpdatedEl.textContent = formatDate(timestamp);
}

function renderChanges(changesPayload) {
  const { changes = [], generated_at: generatedAt } = changesPayload || {};

  changesList.innerHTML = "";

  if (!changes.length) {
    changesEmpty.hidden = false;
    return;
  }

  changesEmpty.hidden = true;

  changes.forEach((change) => {
    const item = document.createElement("li");
    item.className = "change-item";
    const provider = change.provider ? `${change.provider} — ` : "";
    item.innerHTML = `
      <strong>${provider}${change.model || "Unknown model"}</strong><br />
      ${change.description || "Updated pricing."}
      ${change.source ? `<div class="source"><a href="${change.source}" target="_blank" rel="noreferrer noopener">Source</a></div>` : ""}
    `;
    changesList.append(item);
  });

  if (generatedAt) {
    changesTimestamp.textContent = `Reported ${formatDate(generatedAt)}`;
  }
}

async function loadData() {
  try {
    const [pricingResponse, diffResponse] = await Promise.all([
      fetch("data/prices.latest.json"),
      fetch("data/diffs/latest.json"),
    ]);

    if (!pricingResponse.ok || !diffResponse.ok) {
      throw new Error("One or more pricing endpoints returned an error response.");
    }

    const pricingJson = await pricingResponse.json();
    const diffJson = await diffResponse.json();

    pricingData = pricingJson.prices || [];
    buildFilters();
    renderTable();
    applyFilters();
    updateLastUpdated(pricingJson.last_updated || pricingJson.generated_at);
    renderChanges(diffJson);
  } catch (error) {
    console.error("Failed to load data", error);
    lastUpdatedEl.textContent = "Unable to load data";
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadData);
} else {
  loadData();
}
