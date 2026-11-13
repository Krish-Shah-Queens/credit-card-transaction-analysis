import test from 'node:test';
import assert from 'node:assert/strict';
import {calculate, summarize, csv, evaluationMetrics} from './analytics.mjs';

const groups = [[0,0,0,1], [1,1,10000,2], [3,0,100000,1]];
const filters = {from:0,to:3,min:0,max:100000,label:'all'};

test('frequency counts preserve all observations and exact monetary totals',()=>{
  const s=summarize(groups);
  assert.equal(s.count,4);assert.equal(s.total,120000);assert.equal(s.fraud,2);
  assert.equal(s.zero,1);assert.equal(s.mean,30000);assert.equal(s.median,10000);
  assert.ok(Math.abs(s.p95-86500)<1e-6);assert.equal(s.fraudRate,50);
});

test('inclusive time and exact amount filters preserve boundaries',()=>{
  const r=calculate(groups,{...filters,from:1,min:10000,max:10000});
  assert.equal(r.summary.count,2);assert.equal(r.summary.median,10000);
  assert.equal(r.summary.total,20000);assert.equal(r.summary.fraudRate,100);
  assert.equal(r.comparison[0].count,0);assert.equal(r.comparison[1].count,2);
});

test('label filters affect selected results while comparison retains both labels',()=>{
  const r=calculate(groups,{...filters,label:'0'});
  assert.equal(r.summary.count,2);assert.equal(r.summary.fraud,0);
  assert.equal(r.summary.median,50000);assert.equal(r.baseCount,4);
  assert.deepEqual(r.comparison.map(c=>c.count),[2,2]);
});

test('zero hours are represented and rate changes guard zero denominators',()=>{
  const {hours}=calculate(groups,filters);
  assert.deepEqual(hours.map(h=>h.count),[1,2,0,1]);
  assert.deepEqual(hours.map(h=>h.change),[null,100,-100,null]);
  assert.equal(hours[2].rate,null);
});

test('amount bands conserve count and amount at exact band boundaries',()=>{
  const rows=[0,999,1000,4999,5000,9999,10000,49999,50000].map(a=>[0,0,a,1]);
  const r=calculate(rows,filters);
  assert.deepEqual(r.bands.map(b=>b.count),[2,2,2,2,1]);
  assert.equal(r.bands.reduce((sum,b)=>sum+b.count,0),r.summary.count);
  assert.equal(r.bands.reduce((sum,b)=>sum+b.total,0),r.summary.total);
});

test('empty selections have zero counts and undefined summary measures',()=>{
  const r=calculate(groups,{...filters,min:1,max:9999});
  assert.equal(r.summary.count,0);assert.equal(r.summary.total,0);
  assert.equal(r.summary.mean,null);assert.equal(r.summary.median,null);
  assert.equal(r.summary.p95,null);assert.equal(r.summary.fraudRate,null);
});

test('CSV escaping preserves quotes, commas and empty values',()=>{
  assert.equal(csv([['a,b','quoted "value"',null]],['first','second','third']),
    '"first","second","third"\r\n"a,b","quoted ""value""",""');
});

test('model flags are evaluated against separate source labels',()=>{
  const m=evaluationMetrics([.5,54,10,20,56662]);
  assert.equal(m.alerts,64);assert.equal(m.precision,84.375);
  assert.ok(Math.abs(m.recall-72.97297297297297)<1e-8);
  assert.equal(evaluationMetrics([1,0,0,74,56672]).precision,null);
});
