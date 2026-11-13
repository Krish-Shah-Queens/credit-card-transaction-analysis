// Pure, testable calculations. Amounts stay in integer cents until formatting.
export function matchesBase(row, filters) {
  return row[0] >= filters.from && row[0] <= filters.to && row[2] >= filters.min && row[2] <= filters.max;
}

export function matchesLabel(row, label) {
  return label === 'all' || row[1] === Number(label);
}

export function quantile(histogram, count, p) {
  if (!count) return null;
  const position = (count - 1) * p;
  const lower = Math.floor(position), upper = Math.ceil(position);
  let accumulated = 0, low, high;
  for (const [amount, frequency] of [...histogram].sort((a, b) => a[0] - b[0])) {
    accumulated += frequency;
    if (low === undefined && accumulated > lower) low = amount;
    if (accumulated > upper) { high = amount; break; }
  }
  return low + (high - low) * (position - lower);
}

export function summarize(rows) {
  const histogram = new Map();
  let count = 0, total = 0, fraud = 0, zero = 0, maximum = null, minimum = null;
  for (const [, label, amount, frequency] of rows) {
    count += frequency; total += amount * frequency; fraud += label * frequency;
    if (amount === 0) zero += frequency;
    maximum = maximum === null ? amount : Math.max(maximum, amount);
    minimum = minimum === null ? amount : Math.min(minimum, amount);
    histogram.set(amount, (histogram.get(amount) || 0) + frequency);
  }
  return {count, total, fraud, zero, maximum, minimum,
    mean: count ? total / count : null,
    median: quantile(histogram, count, .5), p95: quantile(histogram, count, .95),
    fraudRate: count ? 100 * fraud / count : null};
}

export function calculate(groups, filters) {
  const base = [], selected = [], classes = [[], []];
  const hours = Array.from({length: filters.to - filters.from + 1}, (_, i) => ({
    hour: filters.from + i, count: 0, total: 0, fraud: 0,
  }));
  const bands = ['0 to <10', '10 to <50', '50 to <100', '100 to <500', '500+']
    .map(label => ({label, count: 0, total: 0, fraud: 0}));
  for (const row of groups) {
    if (!matchesBase(row, filters)) continue;
    base.push(row); classes[row[1]].push(row);
    if (!matchesLabel(row, filters.label)) continue;
    selected.push(row);
    const [hour, label, amount, count] = row;
    const h = hours[hour - filters.from];
    h.count += count; h.total += amount * count; h.fraud += label * count;
    const b = bands[amount < 1000 ? 0 : amount < 5000 ? 1 : amount < 10000 ? 2 : amount < 50000 ? 3 : 4];
    b.count += count; b.total += amount * count; b.fraud += label * count;
  }
  for (let i = 0; i < hours.length; i++) {
    const h = hours[i], previous = hours[i - 1];
    h.rate = h.count ? 100 * h.fraud / h.count : null;
    h.change = previous?.count ? 100 * (h.count - previous.count) / previous.count : null;
  }
  return {summary: summarize(selected), comparison: classes.map(summarize), hours, bands, selected,
    baseCount: base.reduce((n, row) => n + row[3], 0)};
}

export function csv(rows, headers) {
  const escape = value => '"' + String(value ?? '').replaceAll('"', '""') + '"';
  return [headers.map(escape).join(','), ...rows.map(row => row.map(escape).join(','))].join('\r\n');
}
