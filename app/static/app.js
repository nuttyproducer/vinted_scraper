"use strict";

const state = {
  items: [], // full item DTOs from the last search
  selected: new Set(), // selected item ids
};

const els = {
  searchInput: document.getElementById("search-input"),
  brandSelect: document.getElementById("brand-select"),
  priceMin: document.getElementById("price-min"),
  priceMax: document.getElementById("price-max"),
  conditionSelect: document.getElementById("condition-select"),
  orderSelect: document.getElementById("order-select"),
  searchBtn: document.getElementById("search-btn"),
  itemsGrid: document.getElementById("items-grid"),
  status: document.getElementById("status"),
  exportBtn: document.getElementById("export-btn"),
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

function renderCards() {
  els.itemsGrid.innerHTML = "";
  for (const item of state.items) {
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
    els.itemsGrid.appendChild(card);
  }
  els.status.textContent = state.items.length
    ? `${state.items.length} results`
    : "";
}

function updateExport() {
  const n = state.selected.size;
  els.exportBtn.textContent = `Export ${n} selected → PDF`;
  els.exportBtn.disabled = n === 0;
}

function showCookieModal() {
  els.cookieModal.hidden = false;
}

async function search() {
  const params = new URLSearchParams();
  if (els.searchInput.value) params.set("q", els.searchInput.value);
  if (els.brandSelect.value) params.set("brand", els.brandSelect.value);
  if (els.priceMin.value) params.set("price_min", els.priceMin.value);
  if (els.priceMax.value) params.set("price_max", els.priceMax.value);
  if (els.conditionSelect.value)
    params.set("condition", els.conditionSelect.value);
  params.set("order", els.orderSelect.value);

  try {
    const res = await fetch("/api/search?" + params.toString());
    if (!res.ok) throw new Error(`search failed (${res.status})`);
    state.items = await res.json();
    state.selected.clear();
    renderCards();
    updateExport();
  } catch (err) {
    els.status.textContent = "Search failed. " + err.message;
    showCookieModal();
  }
}

async function loadBrands() {
  try {
    const res = await fetch("/api/brands");
    if (!res.ok) return;
    const brands = await res.json();
    for (const b of brands) {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.title;
      els.brandSelect.appendChild(opt);
    }
  } catch (e) {
    // brand list is optional; search still works without it
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
els.exportBtn.addEventListener("click", exportPdf);
els.cookieSave.addEventListener("click", saveCookie);
els.cookieClose.addEventListener("click", () => {
  els.cookieModal.hidden = true;
});

loadBrands();
updateExport();
