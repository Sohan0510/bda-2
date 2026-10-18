/**
 * Apache Hive Retail Analytics - Frontend Application Logic
 * Integrates with FastAPI Backend REST API
 */

// Global Chart Instances to allow updating/redrawing cleanly
const charts = {};

// Catalog Pagination State
let catalogState = {
  page: 1,
  pageSize: 15,
  totalPages: 1,
  search: '',
  sortBy: 'quantity',
  order: 'desc'
};

// Global Scripts Cache
let hiveScripts = [];

// Helper: Format Currency in GBP (£)
function formatGBP(val) {
  if (val === null || val === undefined || isNaN(val)) return '£0.00';
  return '£' + Number(val).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Helper: Format Integer with commas
function formatInt(val) {
  if (val === null || val === undefined || isNaN(val)) return '0';
  return Number(val).toLocaleString('en-GB');
}

// ---------------------------------------------------------------------------
// Chart Defaults (Dark Theme & Aesthetics)
// ---------------------------------------------------------------------------
if (window.Chart) {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.95)';
  Chart.defaults.plugins.tooltip.titleFont = { family: "'Plus Jakarta Sans', sans-serif", weight: 'bold' };
  Chart.defaults.plugins.tooltip.bodyFont = { family: "'JetBrains Mono', monospace" };
  Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
}

// ---------------------------------------------------------------------------
// Tab Switching
// ---------------------------------------------------------------------------
function initTabs() {
  const tabButtons = document.querySelectorAll('.nav-tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }

      // Trigger chart resize if needed
      window.dispatchEvent(new Event('resize'));
    });
  });
}

// ---------------------------------------------------------------------------
// API Data Fetching & Rendering
// ---------------------------------------------------------------------------

async function fetchOverview() {
  try {
    const res = await fetch('/api/overview');
    if (!res.ok) throw new Error('Failed to load overview data');
    const data = await res.json();

    // Fill KPI Metrics
    document.getElementById('kpi-total-records').innerText = formatInt(data.total_records);
    document.getElementById('kpi-distinct-invoices').innerText = formatInt(data.distinct_invoices);
    document.getElementById('kpi-distinct-products').innerText = formatInt(data.distinct_products);
    document.getElementById('kpi-identified-customers').innerText = formatInt(data.identified_customers);
    document.getElementById('kpi-distinct-countries').innerText = data.distinct_countries;
    document.getElementById('kpi-total-quantity').innerText = formatInt(data.total_quantity_recorded);

    // Financial Highlights
    const fin = data.financial_summary || {};
    document.getElementById('fin-positive-sales').innerText = formatGBP(fin.positive_sales_revenue_gbp);
    document.getElementById('fin-cancellation-adj').innerText = formatGBP(fin.cancellation_adjustment_gbp);
    document.getElementById('fin-net-signed').innerText = formatGBP(fin.signed_revenue_gbp);

  } catch (err) {
    console.error('Error fetching overview:', err);
  }
}

async function renderMonthlyCharts() {
  try {
    const res = await fetch('/api/monthly-sales');
    if (!res.ok) throw new Error('Failed to load monthly sales');
    const resData = await res.json();
    const list = resData.data || [];

    const labels = list.map(d => d.month);
    const posRev = list.map(d => d.positive_sales_revenue_gbp);
    const signedRev = list.map(d => d.signed_revenue_gbp);
    const posQty = list.map(d => d.positive_sales_quantity);
    const invoices = list.map(d => d.distinct_invoices);

    // Render Overview Monthly Trajectory Chart
    const ctxOverview = document.getElementById('chart-overview-monthly');
    if (ctxOverview && !charts.overviewMonthly) {
      charts.overviewMonthly = new Chart(ctxOverview, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Gross Positive Sales (£)',
              data: posRev,
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99, 102, 241, 0.12)',
              fill: true,
              tension: 0.35,
              borderWidth: 3,
              pointBackgroundColor: '#818cf8',
              pointRadius: 4
            },
            {
              label: 'Net Signed Revenue (£)',
              data: signedRev,
              borderColor: '#10b981',
              borderDash: [5, 5],
              tension: 0.35,
              borderWidth: 2,
              pointBackgroundColor: '#34d399',
              pointRadius: 3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.05)' } },
            y: { 
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { callback: v => '£' + (v >= 1000000 ? (v/1000000).toFixed(1) + 'M' : (v/1000).toFixed(0) + 'k') }
            }
          }
        }
      });
    }

    // Render Tab 2 Detailed Monthly Revenue Chart
    const ctxMonthlyRev = document.getElementById('chart-monthly-revenue');
    if (ctxMonthlyRev && !charts.monthlyRev) {
      charts.monthlyRev = new Chart(ctxMonthlyRev, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Gross Positive Revenue (£)',
              data: posRev,
              borderColor: '#6366f1',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              fill: true,
              tension: 0.3,
              borderWidth: 3,
              pointRadius: 5
            },
            {
              label: 'Net Revenue (£)',
              data: signedRev,
              borderColor: '#34d399',
              tension: 0.3,
              borderWidth: 2,
              pointRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { callback: v => '£' + (v/1000).toFixed(0) + 'k' } }
          }
        }
      });
    }

    // Render Tab 2 Units & Invoices Chart
    const ctxMonthlyVol = document.getElementById('chart-monthly-volume');
    if (ctxMonthlyVol && !charts.monthlyVol) {
      charts.monthlyVol = new Chart(ctxMonthlyVol, {
        data: {
          labels,
          datasets: [
            {
              type: 'bar',
              label: 'Units Sold (Quantity)',
              data: posQty,
              backgroundColor: 'rgba(6, 182, 212, 0.7)',
              borderRadius: 6,
              yAxisID: 'y'
            },
            {
              type: 'line',
              label: 'Distinct Invoices',
              data: invoices,
              borderColor: '#f59e0b',
              borderWidth: 3,
              pointBackgroundColor: '#fbbf24',
              pointRadius: 4,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { 
              grid: { color: 'rgba(255,255,255,0.05)' },
              position: 'left',
              ticks: { callback: v => (v/1000).toFixed(0) + 'k' }
            },
            y1: { 
              position: 'right',
              grid: { drawOnChartArea: false },
              ticks: { callback: v => v }
            }
          }
        }
      });
    }

    // Populate Detailed Monthly Table
    const tbody = document.getElementById('tbody-monthly-sales');
    if (tbody) {
      tbody.innerHTML = list.map(item => `
        <tr>
          <td class="mono"><strong>${item.month}</strong></td>
          <td class="mono">${formatGBP(item.positive_sales_revenue_gbp)}</td>
          <td class="mono" style="color: #34d399;">${formatGBP(item.signed_revenue_gbp)}</td>
          <td class="mono" style="color: #f43f5e;">${formatGBP(item.cancellation_adjustment_gbp)}</td>
          <td class="mono">${formatInt(item.positive_sales_quantity)}</td>
          <td class="mono">${formatInt(item.distinct_invoices)}</td>
          <td class="mono">${formatGBP(item.avg_positive_line_value_gbp)}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    console.error('Error rendering monthly charts:', err);
  }
}

async function renderTransactionBreakdown() {
  try {
    const res = await fetch('/api/transactions/summary');
    if (!res.ok) throw new Error('Failed to load transaction summary');
    const data = await res.json();

    const breakdown = data.direction_breakdown || [];
    const labelsMap = {
      'positive_sale': 'Regular Sales',
      'cancellation': 'Cancellations (Inv C)',
      'return_negative_quantity': 'Returns (Qty < 0)'
    };

    const labels = breakdown.map(b => labelsMap[b.line_type] || b.line_type);
    const lineCounts = breakdown.map(b => b.lines);

    const ctxBreakdown = document.getElementById('chart-overview-breakdown');
    if (ctxBreakdown && !charts.overviewBreakdown) {
      charts.overviewBreakdown = new Chart(ctxBreakdown, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data: lineCounts,
            backgroundColor: ['#6366f1', '#f43f5e', '#f59e0b'],
            borderWidth: 2,
            borderColor: '#0e131f'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' }
          },
          cutout: '65%'
        }
      });
    }

    // Fill Tab 6 Returns KPIs
    document.getElementById('kpi-canc-invoices').innerText = formatInt(data.cancellation_invoices_distinct);
    document.getElementById('kpi-canc-lines').innerText = formatInt(data.cancellation_lines);
    const invRate = ((data.cancellation_invoices_distinct / data.total_distinct_invoices) * 100).toFixed(2);
    const lineRate = ((data.cancellation_lines / data.total_lines) * 100).toFixed(2);
    document.getElementById('kpi-canc-inv-rate').innerText = `${invRate}% of total orders`;
    document.getElementById('kpi-canc-line-rate').innerText = `${lineRate}% of total lines`;

  } catch (err) {
    console.error('Error rendering transaction breakdown:', err);
  }
}

async function renderTopProducts() {
  try {
    // 1. Top by Quantity
    const resQ = await fetch('/api/products/top-quantity?limit=15');
    const listQ = await resQ.json();

    const labelsQ = listQ.map(p => p.description && p.description.length > 25 ? p.description.substring(0, 25) + '...' : p.description);
    const qtysQ = listQ.map(p => p.total_quantity);

    const ctxTopQ = document.getElementById('chart-top-quantity');
    if (ctxTopQ && !charts.topQty) {
      charts.topQty = new Chart(ctxTopQ, {
        type: 'bar',
        data: {
          labels: labelsQ.reverse(),
          datasets: [{
            label: 'Units Sold',
            data: qtysQ.reverse(),
            backgroundColor: 'rgba(139, 92, 246, 0.75)',
            hoverBackgroundColor: '#8b5cf6',
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { grid: { color: 'rgba(255,255,255,0.03)' } }
          }
        }
      });
    }

    // 2. Top by Revenue
    const resR = await fetch('/api/products/top-revenue?limit=15');
    const listR = await resR.json();

    const labelsR = listR.map(p => p.description && p.description.length > 25 ? p.description.substring(0, 25) + '...' : p.description);
    const revsR = listR.map(p => p.total_sales_value_gbp);

    const ctxTopR = document.getElementById('chart-top-revenue');
    if (ctxTopR && !charts.topRev) {
      charts.topRev = new Chart(ctxTopR, {
        type: 'bar',
        data: {
          labels: labelsR.reverse(),
          datasets: [{
            label: 'Revenue (£)',
            data: revsR.reverse(),
            backgroundColor: 'rgba(16, 185, 129, 0.75)',
            hoverBackgroundColor: '#10b981',
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { 
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { callback: v => '£' + (v/1000).toFixed(0) + 'k' }
            },
            y: { grid: { color: 'rgba(255,255,255,0.03)' } }
          }
        }
      });
    }

    // 3. Category Split
    const resCat = await fetch('/api/categories');
    const listCat = await resCat.json();
    const ctxCat = document.getElementById('chart-category-split');
    if (ctxCat && !charts.category) {
      charts.category = new Chart(ctxCat, {
        type: 'doughnut',
        data: {
          labels: listCat.map(c => c.product_category),
          datasets: [{
            data: listCat.map(c => c.total_revenue_gbp),
            backgroundColor: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b'],
            borderWidth: 2,
            borderColor: '#0e131f'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom' } },
          cutout: '55%'
        }
      });
    }

  } catch (err) {
    console.error('Error rendering top products:', err);
  }
}

// ---------------------------------------------------------------------------
// Product Catalog Live Search & Pagination
// ---------------------------------------------------------------------------
async function fetchCatalog() {
  try {
    const { page, pageSize, search, sortBy, order } = catalogState;
    const url = `/api/products/catalog?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&order=${order}${search ? '&q=' + encodeURIComponent(search) : ''}`;
    const res = await fetch(url);
    const data = await res.json();

    catalogState.totalPages = data.total_pages || 1;
    document.getElementById('catalog-page-info').innerText = `Showing page ${data.page} of ${catalogState.totalPages} (${formatInt(data.total)} products)`;

    document.getElementById('btn-catalog-prev').disabled = data.page <= 1;
    document.getElementById('btn-catalog-next').disabled = data.page >= catalogState.totalPages;

    const tbody = document.getElementById('tbody-catalog');
    if (tbody) {
      tbody.innerHTML = (data.items || []).map(p => `
        <tr>
          <td class="mono"><strong>${p.stockcode}</strong></td>
          <td>${p.description || '<span style="color:#64748b;">[missing description]</span>'}</td>
          <td class="mono">${formatInt(p.total_quantity)}</td>
          <td class="mono" style="color: #34d399;">${formatGBP(p.total_sales_value_gbp)}</td>
          <td class="mono">${formatInt(p.distinct_invoices)}</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Error fetching catalog:', err);
  }
}

function initCatalogControls() {
  const searchInput = document.getElementById('input-catalog-search');
  const sortSelect = document.getElementById('select-catalog-sort');
  const btnPrev = document.getElementById('btn-catalog-prev');
  const btnNext = document.getElementById('btn-catalog-next');

  let debounceTimer = null;
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        catalogState.search = e.target.value;
        catalogState.page = 1;
        fetchCatalog();
      }, 300);
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      catalogState.sortBy = e.target.value;
      catalogState.page = 1;
      fetchCatalog();
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', () => {
      if (catalogState.page > 1) {
        catalogState.page--;
        fetchCatalog();
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', () => {
      if (catalogState.page < catalogState.totalPages) {
        catalogState.page++;
        fetchCatalog();
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Low-Volume Tail Explorer
// ---------------------------------------------------------------------------
async function fetchLowVolume() {
  try {
    const res = await fetch('/api/products/low-volume');
    const items = await res.json();
    const tbody = document.getElementById('tbody-low-volume');
    if (tbody) {
      tbody.innerHTML = items.slice(0, 20).map(p => `
        <tr>
          <td class="mono">${p.stockcode}</td>
          <td>${p.description || '[no description]'}</td>
          <td class="mono">${p.total_quantity}</td>
          <td class="mono">${formatGBP(p.total_sales_value_gbp)}</td>
          <td class="mono">${p.transaction_lines}</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Error fetching low volume items:', err);
  }
}

// ---------------------------------------------------------------------------
// Country Analytics
// ---------------------------------------------------------------------------
async function fetchCountries() {
  try {
    const res = await fetch('/api/countries/summary');
    const data = await res.json();
    const list = data.countries || [];

    const nonUK = list.filter(c => c.country !== 'United Kingdom' && c.country !== 'Unspecified').slice(0, 15);
    const labels = nonUK.map(c => c.country);
    const revs = nonUK.map(c => c.revenue_gbp);

    const ctxCountry = document.getElementById('chart-country-sales');
    if (ctxCountry && !charts.countrySales) {
      charts.countrySales = new Chart(ctxCountry, {
        type: 'bar',
        data: {
          labels: labels.reverse(),
          datasets: [{
            label: 'Revenue (£)',
            data: revs.reverse(),
            backgroundColor: 'rgba(56, 189, 248, 0.75)',
            hoverBackgroundColor: '#38bdf8',
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { 
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { callback: v => '£' + (v/1000).toFixed(0) + 'k' }
            },
            y: { grid: { color: 'rgba(255,255,255,0.03)' } }
          }
        }
      });
    }

    // Country Table
    const tbody = document.getElementById('tbody-country-summary');
    if (tbody) {
      tbody.innerHTML = list.map(c => `
        <tr>
          <td><strong>${c.country}</strong></td>
          <td class="mono" style="color: #38bdf8;">${formatGBP(c.revenue_gbp)}</td>
          <td class="mono">${formatInt(c.quantity_sold)}</td>
          <td class="mono">${formatInt(c.distinct_invoices)}</td>
          <td class="mono">${formatInt(c.identified_customers)}</td>
          <td class="mono">${formatInt(c.transaction_lines)}</td>
        </tr>
      `).join('');
    }

    // Country Monthly Trend
    renderCountryMonthlyTrend('Germany');

  } catch (err) {
    console.error('Error fetching country data:', err);
  }
}

async function renderCountryMonthlyTrend(countryName) {
  try {
    const res = await fetch(`/api/countries/monthly?country=${encodeURIComponent(countryName)}`);
    const list = await res.json();

    const labels = list.map(m => m.month);
    const revs = list.map(m => m.revenue_gbp);

    const ctxMonthlyCountry = document.getElementById('chart-country-monthly');
    if (!ctxMonthlyCountry) return;

    if (charts.countryMonthly) {
      charts.countryMonthly.data.labels = labels;
      charts.countryMonthly.data.datasets[0].label = `${countryName} Sales (£)`;
      charts.countryMonthly.data.datasets[0].data = revs;
      charts.countryMonthly.update();
    } else {
      charts.countryMonthly = new Chart(ctxMonthlyCountry, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: `${countryName} Sales (£)`,
            data: revs,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            fill: true,
            tension: 0.3,
            borderWidth: 3,
            pointRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { 
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { callback: v => '£' + v.toLocaleString() }
            }
          }
        }
      });
    }
  } catch (err) {
    console.error('Error rendering country monthly trend:', err);
  }
}

// ---------------------------------------------------------------------------
// Transactions Patterns & Cancellations by Country
// ---------------------------------------------------------------------------
async function fetchPatterns() {
  try {
    const res = await fetch('/api/transactions/patterns');
    const data = await res.json();

    // Hourly Pattern Chart
    const hours = (data.hourly_pattern || []).map(h => `${h.hour_of_day}:00`);
    const invCount = (data.hourly_pattern || []).map(h => h.distinct_invoices);

    const ctxHour = document.getElementById('chart-hourly-pattern');
    if (ctxHour && !charts.hourly) {
      charts.hourly = new Chart(ctxHour, {
        type: 'bar',
        data: {
          labels: hours,
          datasets: [{
            label: 'Orders Placed',
            data: invCount,
            backgroundColor: 'rgba(245, 158, 11, 0.75)',
            hoverBackgroundColor: '#f59e0b',
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' } }
          }
        }
      });
    }

    // Weekday vs Weekend Chart
    const days = (data.weekday_vs_weekend || []).map(d => d.day_type.toUpperCase());
    const dayRevs = (data.weekday_vs_weekend || []).map(d => d.signed_revenue_gbp);

    const ctxDay = document.getElementById('chart-weekday-weekend');
    if (ctxDay && !charts.daySplit) {
      charts.daySplit = new Chart(ctxDay, {
        type: 'doughnut',
        data: {
          labels: days,
          datasets: [{
            data: dayRevs,
            backgroundColor: ['#6366f1', '#ec4899'],
            borderWidth: 2,
            borderColor: '#0e131f'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '60%'
        }
      });
    }

    // Cancellations by Country Table
    const resCBC = await fetch('/api/transactions/cancellations-by-country');
    const cbcData = await resCBC.json();
    const tbodyCBC = document.getElementById('tbody-canc-country');
    if (tbodyCBC) {
      tbodyCBC.innerHTML = cbcData.slice(0, 15).map(c => `
        <tr>
          <td><strong>${c.country}</strong></td>
          <td class="mono">${formatInt(c.cancellation_invoices)}</td>
          <td class="mono">${formatInt(c.cancellation_lines)}</td>
          <td class="mono" style="color: #f43f5e;">${formatGBP(c.cancellation_value_gbp)}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    console.error('Error fetching patterns:', err);
  }
}

// ---------------------------------------------------------------------------
// Validation Assertions Checklist
// ---------------------------------------------------------------------------
async function fetchValidationResults() {
  try {
    const res = await fetch('/api/quality/validation');
    const data = await res.json();

    const checks = data.checks || [];
    const passCount = checks.filter(c => c.match).length;
    document.getElementById('val-pass-count').innerText = `${passCount} / ${checks.length}`;

    const tbody = document.getElementById('tbody-validation-checks');
    if (tbody) {
      tbody.innerHTML = checks.map(c => `
        <tr>
          <td class="mono"><strong>${c.check}</strong></td>
          <td><span class="${c.match ? 'badge-pass' : 'badge-fail'}">${c.match ? '✓ PASS (100% MATCH)' : '✗ FAIL'}</span></td>
          <td style="color: #94a3b8; font-size: 0.8rem;">Independent Python recomputation verifies Hive query output</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Error fetching validation results:', err);
  }
}

function initValidationRunner() {
  const btn = document.getElementById('btn-run-validation');
  if (btn) {
    btn.addEventListener('click', async () => {
      btn.innerHTML = '<span>⏳ Executing tests/validate.py...</span>';
      btn.disabled = true;
      try {
        const res = await fetch('/api/hive/run-validation', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          btn.innerHTML = '<span>✓ Completed Successfully!</span>';
          fetchValidationResults();
        } else {
          btn.innerHTML = '<span>⚠️ Validation Reported Discrepancy</span>';
        }
      } catch (err) {
        btn.innerHTML = '<span>✗ Error Running Tests</span>';
        console.error(err);
      } finally {
        setTimeout(() => {
          btn.innerHTML = '<span>🔄 Re-Execute Verification Suite</span>';
          btn.disabled = false;
        }, 3000);
      }
    });
  }
}

// ---------------------------------------------------------------------------
// HiveQL Scripts Catalog
// ---------------------------------------------------------------------------
async function fetchHiveScripts() {
  try {
    const res = await fetch('/api/hive/scripts');
    hiveScripts = await res.json();

    const tbody = document.getElementById('tbody-hive-scripts');
    if (tbody) {
      tbody.innerHTML = hiveScripts.map((s, idx) => `
        <tr>
          <td class="mono"><strong>${s.name}</strong></td>
          <td class="mono">${s.lines} lines</td>
          <td>
            <button class="btn-page" onclick="viewScript(${idx})">View SQL</button>
          </td>
        </tr>
      `).join('');
    }

    if (hiveScripts.length > 0) {
      viewScript(0);
    }
  } catch (err) {
    console.error('Error fetching Hive scripts:', err);
  }
}

window.viewScript = function(idx) {
  if (hiveScripts[idx]) {
    const script = hiveScripts[idx];
    document.getElementById('selected-script-name').innerText = `Viewing: ${script.name}`;
    document.getElementById('code-script-viewer').innerText = script.code;
  }
};

// ---------------------------------------------------------------------------
// Initialization on DOM Ready
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initCatalogControls();
  initValidationRunner();

  // Listen for country selector changes
  const selectCountry = document.getElementById('select-country-trend');
  if (selectCountry) {
    selectCountry.addEventListener('change', (e) => {
      renderCountryMonthlyTrend(e.target.value);
    });
  }

  // Load all data async
  fetchOverview();
  renderMonthlyCharts();
  renderTransactionBreakdown();
  renderTopProducts();
  fetchCatalog();
  fetchLowVolume();
  fetchCountries();
  fetchPatterns();
  fetchValidationResults();
  fetchHiveScripts();
});
