import {calculate, csv, evaluationMetrics} from './analytics.mjs';

const $ = selector => document.querySelector(selector);
const integer = new Intl.NumberFormat('en-US');
const money = new Intl.NumberFormat('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const compact = new Intl.NumberFormat('en-US', {notation: 'compact', maximumFractionDigits: 2});
const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const n = value => integer.format(value);
const amount = cents => cents === null || !Number.isFinite(cents) ? '—' : money.format(cents / 100);
const pct = (value, digits = 2) => value === null || !Number.isFinite(value) ? '—' : `${value.toFixed(digits)}%`;
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const labelPill = isFraud => `<span class="label-pill ${isFraud ? 'fraud' : ''}" title="Original dataset Class = ${isFraud ? 1 : 0}; not a model prediction">${isFraud ? 'Source: fraud' : 'Source: non-fraud'}</span>`;
const viewInfo = {
  overview: ['Overview', 'Payments overview', 'Transaction value, activity, and historical source labels in one place.'],
  activity: ['Transaction activity', 'Transaction activity', 'Explore hourly volumes and inspect the changes behind each peak.'],
  fraud: ['Source fraud labels', 'Historical fraud labels', 'Compare the original Class labels. These are not model predictions.'],
  model: ['Model evaluation', 'Evaluate model predictions', 'Explore the tradeoff between catching fraud labels and creating false alerts.'],
  explorer: ['Data explorer', 'Transaction explorer', 'Search, sort, and export the amount groups behind the analysis.'],
};
let dataset, results, filters, sourceMaximum, sourceLastHour, modelReport, modelThresholdIndex;
let view = 'overview', chartMetric = 'count', search = '', sort = 'amount-desc', page = 1;
const pageSize = 20;
let toastTimer;

function notify(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 4500);
}

function kpi(title, value, sub, footer, iconName, amber = false, extraClass = '') {
  return `<article class="kpi ${amber ? 'amber' : ''} ${extraClass}"><div class="kpi-label">${title}<span class="kpi-icon">${icon(iconName)}</span></div><div class="kpi-number">${value}</div><div class="kpi-sub">${sub}</div><div class="kpi-footer">${footer}</div></article>`;
}

function stats() {
  const s = results.summary;
  return `<div class="kpi-grid">
    ${kpi('Total transaction value', compact.format(s.total / 100), `${amount(s.total)} in total`, 'Transaction amounts · dataset units', 'activity')}
    ${kpi('Transactions', n(s.count), `${n(results.selected.length)} distinct amount groups`, `${filters.to - filters.from + 1} elapsed hours in selection`, 'table')}
    ${kpi('Typical transaction', amount(s.median), `Mean amount: ${amount(s.mean)}`, 'Median · the middle transaction', 'grid')}
    ${kpi('Labeled fraud rate', pct(s.fraudRate, 4), `${n(s.fraud)} transactions labeled fraud`, 'Observed labels · historical sample', 'shield', true)}
  </div>`;
}

function activityChart(metric = 'count', large = false) {
  const rows = results.hours;
  const width = 800, height = large ? 270 : 230;
  const left = 51, right = 9, top = 14, bottom = height - 30;
  const value = h => metric === 'total' ? h.total / 100 : metric === 'rate' ? (h.rate ?? 0) : h.count;
  const maximum = Math.max(1, ...rows.map(value)) * 1.1;
  const plotHeight = bottom - top;
  const step = (width - left - right) / rows.length;
  const barWidth = Math.min(29, step * .58);
  const tick = v => metric === 'rate' ? `${v.toFixed(v < 1 ? 2 : 1)}%` : compact.format(v);
  let output = `<svg class="chart" viewBox="0 0 ${width} ${height}" role="group" aria-label="Interactive transaction activity by elapsed hour. Activate a bar to filter to that hour.">`;
  for (let i = 0; i <= 4; i++) {
    const y = bottom - plotHeight * i / 4;
    output += `<line class="grid-line" x1="${left}" x2="${width-right}" y1="${y}" y2="${y}"/><text x="${left-10}" y="${y+3}" text-anchor="end">${tick(maximum * i / 4)}</text>`;
  }
  const labelStep = rows.length <= 12 ? 1 : rows.length <= 24 ? 2 : 4;
  rows.forEach((h, i) => {
    const barHeight = value(h) / maximum * plotHeight;
    const x = left + step * (i + .5);
    const tip = `Elapsed hour ${h.hour}: ${n(h.count)} transactions, ${amount(h.total)} total amount, ${pct(h.rate, 4)} labeled fraud. Activate to filter to this hour.`;
    output += `<g data-hour="${h.hour}" tabindex="0" role="button" aria-label="${esc(tip)}"><title>${esc(tip)}</title><rect class="bar ${metric==='rate'?'amber':''}" x="${x-barWidth/2}" y="${bottom-barHeight}" width="${barWidth}" height="${Math.max(0,barHeight)}" rx="2"/><rect x="${left+step*i}" y="${top}" width="${step}" height="${plotHeight}" fill="transparent" stroke="none"/></g>`;
    if (i % labelStep === 0 || rows.length === 1) output += `<text x="${x}" y="${height-10}" text-anchor="middle">${h.hour}</text>`;
  });
  output += '</svg>';
  const metricLabel = metric === 'total' ? 'Transaction value' : metric === 'rate' ? 'Labeled fraud rate' : 'Transaction count';
  return `${output}<div class="chart-caption"><span><i class="legend-dot ${metric==='rate'?'amber':''}"></i>${metricLabel}</span><span>Elapsed hours since first transaction · click a bar to filter</span></div>`;
}

function activityPanel(full = false) {
  return `<section class="panel ${full ? 'activity-chart-panel' : ''}"><div class="panel-heading"><div><h2>Transaction activity</h2><p>${full ? 'All hours in the selected range, including hours with no matching transactions.' : 'A closer look at the flow of transactions over time.'}</p></div><div class="chart-controls">${!full ? '<button class="text-button" data-go="activity">Explore '+icon('arrow')+'</button>' : ''}<select class="panel-select" id="chart-metric" aria-label="Activity chart measure"><option value="count" ${chartMetric==='count'?'selected':''}>Transaction count</option><option value="total" ${chartMetric==='total'?'selected':''}>Transaction value</option><option value="rate" ${chartMetric==='rate'?'selected':''}>Fraud rate</option></select></div></div><div class="panel-body">${activityChart(chartMetric,full)}</div>${full ? '<div class="panel-note">Elapsed hours are not local clock times. The final source hour (47) is partial, so a drop there may reflect coverage rather than a change in behavior.</div>' : ''}</section>`;
}

function amountPanel() {
  const max = Math.max(1, ...results.bands.map(b => b.count));
  return `<section class="panel"><div class="panel-heading"><div><h2>What does a typical transaction look like?</h2><p>Transaction counts by amount band.</p></div></div><div class="panel-body"><div class="amount-bars">${results.bands.map(b => `<div class="amount-row" title="${esc(`${b.label} units: ${n(b.count)} transactions, ${n(b.fraud)} fraud labels`)}"><span>${b.label}</span><div class="bar-track"><div class="bar-fill" style="width:${100*b.count/max}%"></div></div><strong>${n(b.count)}</strong></div>`).join('')}</div><div class="mini-band-row">Median <strong>${amount(results.summary.median)}</strong> · 95th percentile <strong>${amount(results.summary.p95)}</strong> · Maximum <strong>${amount(results.summary.maximum)}</strong></div></div></section>`;
}

function comparisonPreview() {
  return `<section class="panel"><div class="panel-heading"><div><h2>How do fraud labels differ?</h2><p>Both labels · selected time and amount range.</p></div><button class="text-button" data-go="fraud">Compare ${icon('arrow')}</button></div><div class="table-wrap"><table><thead><tr><th>Label</th><th class="numeric">Transactions</th><th class="numeric">Mean amount</th><th class="numeric">Median</th></tr></thead><tbody>${results.comparison.map((s,i) => `<tr><td>${labelPill(i)}</td><td class="numeric">${n(s.count)}</td><td class="numeric">${amount(s.mean)}</td><td class="numeric">${amount(s.median)}</td></tr>`).join('')}</tbody></table></div><div class="table-note">Transaction value is not measured financial loss. Comparisons describe this historical dataset.</div></section>`;
}

function overview() {
  const s = results.summary;
  const peak = results.hours.reduce((a,b)=> b.count > a.count ? b : a);
  const skew = s.count && s.mean > s.median ? 'A smaller number of large amounts lift the average above the median.' : 'Compare the mean with the median to understand transaction size.';
  return `${stats()}${s.count ? '' : emptyState()}<div class="panel-grid">${activityPanel()}<section class="panel insight-panel"><div class="panel-heading"><div class="insight-eyebrow"><span>✧</span> THE STORY IN YOUR DATA</div></div><div class="panel-body"><p class="insight-main">${s.count ? `The middle transaction is <strong>${amount(s.median)}</strong>.` : 'No transactions match this selection.'}</p><p class="insight-copy">${s.count ? `The average is ${amount(s.mean)}. ${skew}` : 'Widen the time or amount range, or reset the filters to explore the full dataset.'}</p><div class="insight-divider">${icon('info')}<span>${s.count ? `Activity peaks in elapsed hour ${peak.hour}, with ${n(peak.count)} transactions in your selection. This is an observed pattern, not a forecast.` : 'Every view uses the same selected time and amount range.'}</span></div></div></section></div><div class="panel-grid bottom-grid">${amountPanel()}${comparisonPreview()}</div>`;
}

function labelExplanation() {
  return `<section class="label-provenance"><div>${icon('shield')}<strong>Where do the fraud labels come from?</strong></div><p>The external dataset provides <code>Class</code>: <strong>1 = fraud</strong>, <strong>0 = non-fraud</strong>. We preserve it as <code>is_fraud</code>. The source does not document each case's investigation. Model flags are shown separately under <button class="text-button" data-go="model">Model evaluation ${icon('arrow')}</button>.</p></section>`;
}

function modelDetails() {
  const r=modelReport,m=evaluationMetrics(r.test_curve[modelThresholdIndex]);
  return `<div class="kpi-grid">
    ${kpi('Predicted alerts',n(m.alerts),`${n(m.tp)} source fraud · ${n(m.fp)} source non-fraud`,'Model flags · not confirmed cases','shield')}
    ${kpi('Precision',pct(m.precision,2),'Fraud labels among all model alerts','Higher precision means fewer false alerts','grid')}
    ${kpi('Recall',pct(m.recall,2),`${n(m.tp)} of ${n(m.tp+m.fn)} fraud labels caught`,'Higher recall means fewer missed labels','activity')}
    ${kpi('Missed fraud labels',n(m.fn),'Source Class 1 · model did not flag','False negatives on the test period','shield',true)}
  </div><div class="panel-grid equal"><section class="panel"><div class="panel-heading"><div><h2>Predictions versus source labels</h2><p>Every transaction in the chronological test set.</p></div></div><div class="table-wrap"><table><thead><tr><th>Original source label</th><th class="numeric">Not flagged</th><th class="numeric">Flagged by model</th></tr></thead><tbody><tr><td>${labelPill(0)}</td><td class="numeric">${n(m.tn)}<small class="cell-note">True negatives</small></td><td class="numeric">${n(m.fp)}<small class="cell-note">False positives</small></td></tr><tr><td>${labelPill(1)}</td><td class="numeric">${n(m.fn)}<small class="cell-note">False negatives</small></td><td class="numeric">${n(m.tp)}<small class="cell-note">True positives</small></td></tr></tbody></table></div><div class="table-note">Source labels and model flags are independent columns. A model flag never changes a source label.</div></section><section class="panel"><div class="panel-heading"><div><h2>Why accuracy alone is misleading</h2><p>A baseline that never flags a transaction.</p></div></div><div class="panel-body"><div class="baseline-number">${pct(100*r.always_non_fraud_baseline.accuracy,2)}<span>accuracy · always predict non-fraud</span></div><p class="insight-copy">That baseline catches <strong>zero</strong> fraud labels and misses all <strong>${n(r.splits.test.source_fraud_count)}</strong> in the test set. Use precision, recall, and false alerts to understand performance.</p><div class="mini-band-row">Selected model test average precision: <strong>${r.test_average_precision.toFixed(4)}</strong>.<br>Test fraud prevalence: ${pct(100*r.test_prevalence,4)}. Average precision summarizes the ranked scores, not accuracy.</div></div></section></div><section class="panel"><div class="panel-heading"><div><h2>Review held-out examples</h2><p>Examples selected across the original operating point's outcomes; this is not a representative sample.</p></div></div><div class="table-wrap"><table><thead><tr><th>Local example</th><th>Elapsed hour</th><th class="numeric">Amount</th><th>Original source label</th><th class="numeric">Model score</th><th>Model decision</th></tr></thead><tbody>${r.examples.map(e=>`<tr><td>${esc(e.example_id)}</td><td>Hour ${e.elapsed_hour}</td><td class="numeric">${money.format(e.amount)}</td><td>${labelPill(e.source_label)}</td><td class="numeric">${e.model_score.toFixed(6)}</td><td><span class="prediction-pill ${e.model_score>=m.threshold?'flagged':''}">${e.model_score>=m.threshold?'Flag for review':'Not flagged'}</span></td></tr>`).join('')}</tbody></table></div></section>`;
}

function modelView() {
  const r=modelReport;
  return `<div class="notice">${icon('info')}<span><strong>${esc(r.model_name)}</strong> · ${n(r.splits.test.count)} held-out observations. These are predictions on historical data, not newly confirmed fraud. Analysis filters do not apply to this fixed test set.</span></div><section class="panel model-threshold"><div><h2>Choose a model operating threshold</h2><p>Flag when model score ≥ threshold. Scores are not calibrated probabilities.</p></div><label for="model-threshold">Threshold <strong id="threshold-readout">${r.test_curve[modelThresholdIndex][0].toFixed(3)}</strong></label><input id="model-threshold" type="range" min="0" max="1000" step="1" value="${modelThresholdIndex}" aria-label="Model flag threshold"><button class="button button-ghost" id="use-validation-threshold">Use validation threshold · ${r.recommended_threshold.toFixed(3)}</button><p class="threshold-note">The default maximizes F2 on validation data. Moving the slider explores the test results; it is not a fresh unbiased evaluation.</p></section><div id="model-details">${modelDetails()}</div><section class="panel training-panel"><div class="panel-heading"><div><h2>Trained on the past. Tested on a later period.</h2><p>No random mixing of earlier and later observations.</p></div></div><div class="split-timeline">${Object.entries(r.splits).map(([name,s])=>`<div><span>${name.toUpperCase()}</span><strong>${n(s.count)}</strong><small>${n(s.source_fraud_count)} source fraud labels · seconds ${n(s.first_second)}–${n(s.last_second)}</small></div>`).join('')}</div><div class="panel-body"><p class="insight-copy">Exact source duplicates were removed for modeling (${n(r.split_info.exact_duplicate_rows_removed)} rows). The descriptive analysis still retains all original observations. Equal timestamps stay in one split. Model selection uses validation average precision; the test set is not used for selection.</p><p class="insight-copy">Features: V1–V28 and log-transformed Amount. <strong>Class and Time are excluded from model input.</strong> The PCA features are anonymized, so individual scores cannot be translated into claims about a customer or merchant.</p><details><summary>Limitations and reproducibility</summary><ul>${r.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p>Train the same pipeline with <code>python scripts/train_fraud_model.py</code>. The full Streamlit app includes CSV scoring with the saved model.</p></details></div></section>`;
}

function emptyState() {
  return `<div class="empty-state">${icon('table')}<h2>No matching transactions</h2><p>Try a wider amount or elapsed-hour range.<br>Your original dataset is still available.</p><button class="button button-primary" data-reset>Reset filters</button></div>`;
}

function activity() {
  const hours = results.hours;
  const peak = hours.reduce((a,b)=>b.count>a.count?b:a);
  const gains = hours.filter(h=>h.change!==null&&h.change>0).sort((a,b)=>b.change-a.change);
  const drops = hours.filter(h=>h.change!==null&&h.change<0).sort((a,b)=>a.change-b.change);
  const gain = gains[0], drop = drops[0];
  return `<div class="kpi-grid three-grid">
    ${kpi('Busiest elapsed hour', results.summary.count ? `Hour ${peak.hour}` : '—', results.summary.count ? `${n(peak.count)} transactions` : 'No matching transactions', 'Highest count in your selection', 'activity', false, 'compact')}
    ${kpi('Largest hourly increase',gain ? `+${gain.change.toFixed(1)}%` : '—',gain ? `Hour ${gain.hour-1} → ${gain.hour}` : 'No increase in this selection','Compared with the preceding hour','activity',false,'compact')}
    ${kpi('Largest hourly decrease',drop ? `${drop.change.toFixed(1)}%` : '—',drop ? `Hour ${drop.hour-1} → ${drop.hour}` : 'No decrease in this selection',drop?.hour===sourceLastHour?'Final source hour is partial':'Compared with the preceding hour','activity',true,'compact')}
    </div>${activityPanel(true)}<section class="panel"><div class="panel-heading"><div><h2>The hourly detail</h2><p>Read the exact values behind the activity view.</p></div><span class="small-label">${hours.length} ELAPSED HOURS</span></div><div class="table-wrap"><table><thead><tr><th>Elapsed hour</th><th class="numeric">Transactions</th><th class="numeric">Count change</th><th class="numeric">Total amount</th><th class="numeric">Mean amount</th><th class="numeric">Fraud labels</th><th class="numeric">Fraud rate</th></tr></thead><tbody>${hours.map(h => `<tr><td>Hour ${h.hour}${h.hour===sourceLastHour?' <span class="muted">· partial</span>':''}</td><td class="numeric">${n(h.count)}</td><td class="numeric ${h.change>0?'positive':h.change<0?'negative':'muted'}">${h.change>0?'+':''}${pct(h.change,1)}</td><td class="numeric">${amount(h.total)}</td><td class="numeric">${amount(h.count?h.total/h.count:null)}</td><td class="numeric">${n(h.fraud)}</td><td class="numeric">${pct(h.rate,4)}</td></tr>`).join('')}</tbody></table></div><div class="table-note">Count change compares adjacent hours within the selection. A dash means the previous hour is absent or has zero transactions. Counts can include zero-amount transactions.</div></section>`;
}

function fraud() {
  const [normal, fraud] = results.comparison;
  const baseTotal = normal.count + fraud.count;
  const metrics = [
    ['Transactions',s=>n(s.count)], ['Share of transactions',s=>pct(baseTotal?100*s.count/baseTotal:null,4)],
    ['Total transaction value',s=>amount(s.total)], ['Mean amount',s=>amount(s.mean)],
    ['Median amount',s=>amount(s.median)], ['95th percentile amount',s=>amount(s.p95)],
    ['Maximum amount',s=>amount(s.maximum)], ['Zero-amount transactions',s=>n(s.zero)],
    ['Zero-amount share',s=>pct(s.count?100*s.zero/s.count:null,2)],
  ];
  return `<div class="notice">${icon('info')}<span>Comparing <strong>both labels</strong> within elapsed hours ${filters.from}–${filters.to} and amounts ${amount(filters.min)}–${amount(filters.max)}. The label filter applies to the other views; this comparison always keeps both groups visible.</span></div><div class="panel-grid equal">${results.comparison.map((s,i)=>`<section class="panel compare-tile ${i?'fraud':''}"><div class="compare-top">${labelPill(i)}<span class="small-label">${pct(baseTotal?100*s.count/baseTotal:null,4)} OF SELECTION</span></div><div class="big-count">${n(s.count)}</div><p>transactions ${i?'with a fraud label':'with a non-fraud label'}</p><div class="compare-progress" title="${esc(pct(baseTotal?100*s.count/baseTotal:null,4))} of selected transactions"><div style="width:${baseTotal?100*s.count/baseTotal:0}%"></div></div><div class="compare-stats"><span>Typical amount (median)<strong>${amount(s.median)}</strong></span><span>Average amount (mean)<strong>${amount(s.mean)}</strong></span></div></section>`).join('')}</div><section class="panel comparison-table"><div class="panel-heading"><div><h2>Compare the full amount profile</h2><p>Exact calculations from all matching transactions in each group.</p></div></div><div class="table-wrap"><table><thead><tr><th>Measure</th><th class="numeric">${labelPill(0)}</th><th class="numeric">${labelPill(1)}</th></tr></thead><tbody>${metrics.map(([name,format])=>`<tr><td>${name}</td><td class="numeric">${format(normal)}</td><td class="numeric">${format(fraud)}</td></tr>`).join('')}</tbody></table></div></section><section class="panel insight-panel"><div class="panel-heading"><div class="insight-eyebrow"><span>✧</span> HOW TO READ THIS COMPARISON</div></div><div class="panel-body"><p class="insight-copy">${normal.count&&fraud.count?`Fraud-labeled transactions have a median amount of <strong>${amount(fraud.median)}</strong>, compared with <strong>${amount(normal.median)}</strong> for non-fraud transactions. Their mean is <strong>${amount(fraud.mean)}</strong>, compared with <strong>${amount(normal.mean)}</strong>. The mean and median describe different parts of the amount distribution.`:'One or both labels have no transactions in this time and amount range. Widen the filters to compare both groups.'}</p><div class="insight-divider">${icon('shield')}<span>A fraud label is an observed outcome, not a live risk score. Amounts alone do not establish why fraud occurred, and the transaction value is not a measure of losses.</span></div></div></section>`;
}

function explorer() {
  return `<div class="notice">${icon('info')}<span>This explorer shows <strong>amount groups</strong>, not unique source transaction IDs. Each row combines transactions with the same elapsed hour, label, and exact amount. The “Transactions” column tells you how many observations it represents.</span></div><section class="panel"><div class="panel-heading"><div><h2>Explore the underlying amounts</h2><p id="explorer-summary">${n(results.selected.length)} groups representing ${n(results.summary.count)} transactions.</p></div><span class="small-label">ALL MATCHING OBSERVATIONS</span></div><div class="explorer-toolbar"><label class="search-box"><span aria-hidden="true">⌕</span><input id="explorer-search" type="search" placeholder="Search an amount or elapsed hour…" aria-label="Search an amount or elapsed hour" value="${esc(search)}"></label><select class="panel-select" id="explorer-sort" aria-label="Sort amount groups">${[['amount-desc','Largest amount first'],['amount-asc','Smallest amount first'],['count-desc','Most transactions first'],['hour-asc','Earliest hour first'],['hour-desc','Latest hour first']].map(([v,label])=>`<option value="${v}" ${sort===v?'selected':''}>${label}</option>`).join('')}</select></div><div class="table-wrap"><table><thead><tr><th>Elapsed hour</th><th>Transaction label</th><th class="numeric">Exact amount</th><th class="numeric">Transactions</th><th class="numeric">Group total value</th></tr></thead><tbody id="explorer-rows"></tbody></table></div><div class="pagination"><span id="page-count"></span><div class="pagination-actions"><button id="previous-page">← Previous</button><span id="page-position"></span><button id="next-page">Next →</button></div></div></section>`;
}

function explorerRows() {
  let rows = [...results.selected];
  const q = search.trim().toLowerCase();
  if (q) rows = rows.filter(row=>String(row[0]).includes(q)||String(row[2]/100).includes(q)||amount(row[2]).replaceAll(',','').includes(q));
  const comparator = {
    'amount-desc':(a,b)=>b[2]-a[2]||a[0]-b[0]||a[1]-b[1],
    'amount-asc':(a,b)=>a[2]-b[2]||a[0]-b[0]||a[1]-b[1],
    'count-desc':(a,b)=>b[3]-a[3]||b[2]-a[2]||a[0]-b[0],
    'hour-asc':(a,b)=>a[0]-b[0]||a[2]-b[2]||a[1]-b[1],
    'hour-desc':(a,b)=>b[0]-a[0]||a[2]-b[2]||a[1]-b[1],
  }[sort];
  rows.sort(comparator);
  return rows;
}

function updateExplorer() {
  const rows = explorerRows();
  const pages = Math.max(1,Math.ceil(rows.length/pageSize));
  page = Math.min(page,pages);
  const from = (page-1)*pageSize;
  $('#explorer-rows').innerHTML = rows.length ? rows.slice(from,from+pageSize).map(([h,label,cents,count])=>`<tr><td>Hour ${h}</td><td>${labelPill(label)}</td><td class="numeric">${amount(cents)}</td><td class="numeric">${n(count)}</td><td class="numeric">${amount(cents*count)}</td></tr>`).join('') : '<tr><td colspan="5"><div class="empty-state"><h2>No matching amount groups</h2><p>Try a different search or widen the filters.</p></div></td></tr>';
  $('#page-count').textContent = rows.length ? `${n(from+1)}–${n(Math.min(from+pageSize,rows.length))} of ${n(rows.length)} amount groups` : '0 matching groups';
  $('#page-position').textContent = `${n(page)} / ${n(pages)}`;
  $('#previous-page').disabled = page<=1;
  $('#next-page').disabled = page>=pages;
  const represented = rows.reduce((sum,row)=>sum+row[3],0);
  $('#explorer-summary').textContent = `${n(rows.length)} groups representing ${n(represented)} transactions${qNote()}.`;
}

function qNote() { return search.trim() ? ' matching your search' : ''; }

function render() {
  if (!results) return;
  const info = viewInfo[view];
  $('#breadcrumb-view').textContent = info[0];
  $('#page-title').textContent = info[1];
  $('#page-subtitle').textContent = info[2];
  document.title = `${info[0]} — Ledger Transaction Explorer`;
  document.querySelectorAll('.nav-item').forEach(b=>{
    b.classList.toggle('active',b.dataset.view===view);
    if(b.dataset.view===view) b.setAttribute('aria-current','page'); else b.removeAttribute('aria-current');
  });
  $('#filter-form').hidden=view==='model';
  $('#period-shortcuts').hidden=view==='model';
  $('#reset-filters').hidden=view==='model';
  const count = view==='fraud' ? results.baseCount : results.summary.count;
  $('#filter-status').innerHTML = `<strong>${n(count)} transactions</strong> · elapsed hours ${filters.from}–${filters.to}${view==='fraud'?' · both labels compared':filters.label==='all'?' · all labels':filters.label==='1'?' · fraud-labeled only':' · non-fraud only'}`;
  if(view==='model') $('#filter-status').textContent=`${n(modelReport.splits.test.count)} held-out observations · fixed chronological test period`;
  $('#content').innerHTML = `${view==='fraud'?labelExplanation():''}${{overview,activity,fraud,model:modelView,explorer}[view]()}`;
  document.querySelectorAll('[data-period]').forEach(b=>b.classList.toggle('selected',filters.from===Number(b.dataset.from)&&filters.to===Number(b.dataset.to)));
  $('#content').setAttribute('aria-busy','false');
  if(view==='explorer') updateExplorer();
}

function changeView(next) {
  if (!viewInfo[next]) return;
  view=next;
  history.replaceState(null,'',`#${view}`);
  render();
}

function applyFilters(event) {
  event?.preventDefault();
  if(!dataset) return;
  const from=Number($('#hour-from').value), to=Number($('#hour-to').value);
  const minValue=$('#min-amount').value, maxValue=$('#max-amount').value;
  const min=Number(minValue), max=Number(maxValue);
  let error='';
  if(from>to) error='The first elapsed hour must be earlier than, or equal to, the last hour.';
  else if(minValue===''||maxValue===''||!Number.isFinite(min)||!Number.isFinite(max)||min<0||max<0) error='Enter valid, non-negative minimum and maximum amounts.';
  else if(min>max) error='The minimum amount must be less than, or equal to, the maximum amount.';
  if(error){$('#error').textContent=error;$('#error').hidden=false;return;}
  $('#error').hidden=true;
  filters={from,to,label:$('#label-filter').value,min:Math.round(min*100),max:Math.round(max*100)};
  results=calculate(dataset.groups,filters);page=1;render();
}

function resetFilters() {
  if(!dataset)return;
  $('#hour-from').value=0;$('#hour-to').value=sourceLastHour;$('#label-filter').value='all';
  $('#min-amount').value='0';$('#max-amount').value=(sourceMaximum/100).toFixed(2);
  search='';page=1;applyFilters();
}

function exportData() {
  if(!results)return;
  const provenance=['ULB/Worldline 2013','https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud','ODbL 1.0 / DbCL 1.0'];
  let headers,rows;
  if(view==='model'){
    headers=['threshold','true_positives','false_positives','false_negatives','true_negatives','source_dataset','source_url','data_license'];
    rows=modelReport.test_curve.map(row=>[...row,...provenance]);
  }else if(view==='explorer'){
    headers=['elapsed_hour','label','amount_dataset_units','transaction_count','group_total_amount', 'source_dataset','source_url','data_license'];
    rows=explorerRows().map(([h,label,cents,count])=>[h,label?'fraud':'non-fraud',(cents/100).toFixed(2),count,(cents*count/100).toFixed(2),...provenance]);
  }else if(view==='fraud'){
    headers=['label','transaction_count','total_amount','mean_amount','median_amount','p95_amount','maximum_amount','zero_amount_count','source_dataset','source_url','data_license'];
    rows=results.comparison.map((s,i)=>[i?'fraud':'non-fraud',s.count,...[s.total,s.mean,s.median,s.p95,s.maximum].map(v=>v===null?'':(v/100).toFixed(2)),s.zero,...provenance]);
  }else{
    headers=['elapsed_hour','transaction_count','total_amount','mean_amount','fraud_count','fraud_rate_pct','count_change_pct','source_dataset','source_url','data_license'];
    rows=results.hours.map(h=>[h.hour,h.count,(h.total/100).toFixed(2),h.count?(h.total/h.count/100).toFixed(2):'',h.fraud,h.rate,h.change,...provenance]);
  }
  const blob=new Blob(['\uFEFF',csv(rows,headers)],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=`ulb-worldline-${view}-hours-${filters.from}-${filters.to}.csv`;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
  notify(`Exported ${n(rows.length)} ${view==='explorer'?'amount groups':'summary rows'} with source attribution.`);
}

function openMethodology(){ $('#methodology').showModal(); }
$('#source-open').addEventListener('click',openMethodology);
$('#units-info').addEventListener('click',openMethodology);
$('#methodology-open').addEventListener('click',openMethodology);
$('.close-dialog').addEventListener('click',()=>$('#methodology').close());
$('#methodology').addEventListener('click',event=>{if(event.target===$('#methodology')){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});
$('#filter-form').addEventListener('submit',applyFilters);
$('#reset-filters').addEventListener('click',resetFilters);
$('#export').addEventListener('click',exportData);
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>changeView(b.dataset.view)));
document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>{$('#hour-from').value=b.dataset.from;$('#hour-to').value=b.dataset.to;applyFilters();}));
$('#content').addEventListener('click',event=>{
  const go=event.target.closest('[data-go]');if(go){changeView(go.dataset.go);return;}
  if(event.target.closest('#use-validation-threshold')){modelThresholdIndex=modelReport.recommended_index;render();return;}
  const hour=event.target.closest('[data-hour]');if(hour){$('#hour-from').value=hour.dataset.hour;$('#hour-to').value=hour.dataset.hour;applyFilters();return;}
  if(event.target.closest('[data-reset]')){resetFilters();return;}
  if(event.target.closest('#previous-page')){page--;updateExplorer();}
  if(event.target.closest('#next-page')){page++;updateExplorer();}
});
$('#content').addEventListener('keydown',event=>{const hour=event.target.closest('[data-hour]');if(hour&&(event.key==='Enter'||event.key===' ')){event.preventDefault();$('#hour-from').value=hour.dataset.hour;$('#hour-to').value=hour.dataset.hour;applyFilters();}});
$('#content').addEventListener('change',event=>{
  if(event.target.id==='chart-metric'){chartMetric=event.target.value;render();}
  if(event.target.id==='explorer-sort'){sort=event.target.value;page=1;updateExplorer();}
});
$('#content').addEventListener('input',event=>{
  if(event.target.id==='explorer-search'){search=event.target.value;page=1;updateExplorer();}
  if(event.target.id==='model-threshold'){modelThresholdIndex=Number(event.target.value);$('#threshold-readout').textContent=modelReport.test_curve[modelThresholdIndex][0].toFixed(3);$('#model-details').innerHTML=modelDetails();}
});
window.addEventListener('hashchange',()=>changeView(location.hash.slice(1)));

async function start() {
  const controls=[...document.querySelectorAll('#filter-form input,#filter-form select,#filter-form button,#export,#reset-filters')];
  controls.forEach(c=>c.disabled=true);
  try{
    const [response,modelResponse]=await Promise.all([fetch('./data/transactions.json'),fetch('./data/model_evaluation.json')]);
    if(!modelResponse.ok)throw new Error('The model evaluation report could not be loaded.');
    modelReport=await modelResponse.json();modelThresholdIndex=modelReport.recommended_index;
    if(!response.ok)throw new Error(`Dataset request failed (${response.status}).`);
    const data=await response.json();
    if(data.schema_version!==1||!Array.isArray(data.groups)||!data.groups.length)throw new Error('The dashboard data has an unsupported format.');
    let count=0,total=0;
    for(const row of data.groups){
      if(row.length!==4||!row.every(Number.isSafeInteger)||row[0]<0||![0,1].includes(row[1])||row[2]<0||row[3]<=0)throw new Error('The dashboard data contains an invalid amount group.');
      count+=row[3];total+=row[2]*row[3];
    }
    if(count!==data.metadata.transaction_count||total!==data.metadata.total_amount_cents)throw new Error('The dashboard data does not reconcile with its source totals.');
    dataset=data;sourceMaximum=data.groups.reduce((max,row)=>Math.max(max,row[2]),0);
    sourceLastHour=Math.floor(data.metadata.last_elapsed_second/3600);
    if(data.groups.some(row=>row[0]>sourceLastHour))throw new Error('An amount group falls outside the source observation window.');
    const options=Array.from({length:sourceLastHour+1},(_,i)=>`<option value="${i}">Hour ${i}</option>`).join('');
    $('#hour-from').innerHTML=options;$('#hour-to').innerHTML=options;
    $('#dataset-count').textContent=n(count);
    $('#source-facts').innerHTML=`<div class="source-facts"><span>Source observations<strong>${n(count)}</strong></span><span>Fraud labels<strong>${n(data.groups.reduce((sum,row)=>sum+row[1]*row[3],0))}</strong></span><span>Exact duplicate extra rows<strong>${n(data.metadata.exact_duplicate_extra_rows)} · retained</strong></span><span>Zero-amount rows<strong>${n(data.metadata.zero_amount_rows)} · retained</strong></span></div>`;
    controls.forEach(c=>c.disabled=false);
    const requested=location.hash.slice(1);if(viewInfo[requested])view=requested;
    resetFilters();
  }catch(error){
    $('#filter-status').textContent='Dataset unavailable';
    $('#content').setAttribute('aria-busy','false');
    $('#content').innerHTML=`<div class="empty-state">${icon('info')}<h2>We couldn’t load the dataset.</h2><p>${esc(error.message)}<br>Reload the page to try again. If running locally, serve the dashboard folder over HTTP.</p><button class="button button-primary" id="retry-load">Try again</button></div>`;
    $('#retry-load').addEventListener('click',()=>location.reload());
  }
}

start();
