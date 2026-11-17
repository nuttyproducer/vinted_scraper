"use strict";

const PER_PAGE = 96;

const state = {
  items: [], // all loaded item DTOs from the current search
  selected: new Set(), // selected item ids
  page: 1,
  hasMore: false,
  renderedCount: 0,
  brandFilter: "", // client-side brand filter ("" = all)
};

const els = {
  searchInput: document.getElementById("search-input"),
  brandSelect: document.getElementById("brand-select"),
  priceMin: document.getElementById("price-min"),
  priceMax: document.getElementById("price-max"),
  conditionSelect: document.getElementById("condition-select"),
  orderSelect: document.getElementById("order-select"),
  marketsAll: document.getElementById("markets-all"),
  marketChecks: Array.from(document.querySelectorAll(".market-check[value]")),
  searchBtn: document.getElementById("search-btn"),
  itemsGrid: document.getElementById("items-grid"),
  status: document.getElementById("status"),
  exportBtn: document.getElementById("export-btn"),
  loadMoreBtn: document.getElementById("load-more"),
  cookieModal: document.getElementById("cookie-modal"),
  cookieInput: document.getElementById("cookie-input"),
  cookieSave: document.getElementById("cookie-save"),
  cookieClose: document.getElementById("cookie-close"),
};

function fmtPrice(item) {
  if (item.price == null) return "";
  const amount = Number(item.price).toFixed(2).replace(/\.00$/, "");
  return item.currency ? `${amount} ${item.currency}` : amount;
}

function buildCard(item) {
  const card = document.createElement("article");
  card.className = "card";

  const check = document.createElement("input");
  check.type = "checkbox";
  check.className = "card-check";
  check.checked = state.selected.has(item.id);
  check.addEventListener("change", () => {
    if (check.checked) state.selected.add(item.id);
    else state.selected.delete(item.id);
    updateExport();
  });

  const img = document.createElement("img");
  img.className = "card-img";
  img.loading = "lazy";
  if (item.photo_url) img.src = item.photo_url;
  img.alt = item.title || "";
  img.style.visibility = item.photo_url ? "visible" : "hidden";

  const body = document.createElement("div");
  body.className = "card-body";

  const title = document.createElement("a");
  title.className = "card-title";
  title.href = item.url || "#";
  title.target = "_blank";
  title.rel = "noopener";
  title.textContent = item.title || `Item ${item.id}`;

  const price = document.createElement("div");
  price.className = "card-price";
  price.textContent = fmtPrice(item);

  const meta = document.createElement("div");
  meta.className = "card-meta";
  meta.textContent = [item.brand, item.size, item.condition]
    .filter(Boolean)
    .join(" · ");

  body.append(title, price, meta);
  card.append(check, img, body);
  return card;
}

function getVisibleItems() {
  if (!state.brandFilter) return state.items;
  return state.items.filter((i) => i.brand === state.brandFilter);
}

function renderCards(reset) {
  if (reset) {
    els.itemsGrid.innerHTML = "";
    state.renderedCount = 0;
  }
  for (let i = state.renderedCount; i < state.items.length; i++) {
    const item = state.items[i];
    if (!state.brandFilter || item.brand === state.brandFilter) {
      els.itemsGrid.appendChild(buildCard(item));
    }
  }
  state.renderedCount = state.items.length;
  els.status.textContent = `${getVisibleItems().length} results`;
  els.loadMoreBtn.hidden = !state.hasMore;
}

function updateBrandOptions() {
  const current = state.brandFilter;
  const brands = [];
  const seen = new Set();
  for (const item of state.items) {
    if (item.brand && !seen.has(item.brand)) {
      seen.add(item.brand);
      brands.push(item.brand);
    }
  }
  brands.sort();
  els.brandSelect.innerHTML = '<option value="">All brands</option>';
  for (const b of brands) {
    const opt = document.createElement("option");
    opt.value = b;
    opt.textContent = b;
    els.brandSelect.appendChild(opt);
  }
  if (brands.includes(current)) {
    els.brandSelect.value = current;
  } else {
    els.brandSelect.value = "";
    state.brandFilter = "";
  }
}

function updateExport() {
  const n = state.selected.size;
  els.exportBtn.textContent = `Export ${n} selected → PDF`;
  els.exportBtn.disabled = n === 0;
}

function getSelectedMarkets() {
  return els.marketChecks
    .filter((c) => c.checked)
    .map((c) => c.value)
    .join(",");
}

function buildParams() {
  const params = new URLSearchParams();
  if (els.searchInput.value) params.set("q", els.searchInput.value);
  if (els.priceMin.value) params.set("price_min", els.priceMin.value);
  if (els.priceMax.value) params.set("price_max", els.priceMax.value);
  if (els.conditionSelect.value)
    params.set("condition", els.conditionSelect.value);
  const markets = getSelectedMarkets();
  if (markets) params.set("markets", markets);
  params.set("order", els.orderSelect.value);
  params.set("per_page", String(PER_PAGE));
  return params;
}

function showCookieModal() {
  els.cookieModal.hidden = false;
}

async function search() {
  const params = buildParams();
  params.set("page", "1");
  try {
    const res = await fetch("/api/search?" + params.toString());
    if (!res.ok) throw new Error(`search failed (${res.status})`);
    const data = await res.json();
    state.items = data.items;
    state.page = 1;
    state.hasMore = data.has_more;
    state.brandFilter = "";
    state.selected.clear();
    updateBrandOptions();
    renderCards(true);
    updateExport();
  } catch (err) {
    els.status.textContent = "Search failed. " + err.message;
    showCookieModal();
  }
}

async function loadMore() {
  const params = buildParams();
  params.set("page", String(state.page + 1));
  els.loadMoreBtn.disabled = true;
  try {
    const res = await fetch("/api/search?" + params.toString());
    if (!res.ok) throw new Error(`search failed (${res.status})`);
    const data = await res.json();
    state.items = state.items.concat(data.items);
    state.page += 1;
    state.hasMore = data.has_more;
    updateBrandOptions();
    renderCards();
  } catch (err) {
    els.status.textContent = "Search failed. " + err.message;
  } finally {
    els.loadMoreBtn.disabled = false;
  }
}

async function exportPdf() {
  const selected = state.items.filter((i) => state.selected.has(i.id));
  if (!selected.length) return;
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: selected }),
    });
    if (!res.ok) throw new Error(`export failed (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vinted-price-research.pdf";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    els.status.textContent = "Export failed. " + err.message;
    showCookieModal();
  }
}

async function saveCookie() {
  const cookie = els.cookieInput.value.trim();
  if (!cookie) return;
  const res = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cookie }),
  });
  if (res.ok) {
    els.cookieModal.hidden = true;
    await search();
  }
}

els.searchBtn.addEventListener("click", search);
els.searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") search();
});
els.brandSelect.addEventListener("change", () => {
  state.brandFilter = els.brandSelect.value;
  renderCards(true);
});
els.conditionSelect.addEventListener("change", search);
els.orderSelect.addEventListener("change", search);
els.priceMin.addEventListener("change", search);
els.priceMax.addEventListener("change", search);
els.marketsAll.addEventListener("change", () => {
  els.marketChecks.forEach((c) => (c.checked = els.marketsAll.checked));
  search();
});
els.marketChecks.forEach((c) => c.addEventListener("change", search));
els.loadMoreBtn.addEventListener("click", loadMore);
els.exportBtn.addEventListener("click", exportPdf);
els.cookieSave.addEventListener("click", saveCookie);
els.cookieClose.addEventListener("click", () => {
  els.cookieModal.hidden = true;
});

updateExport();
