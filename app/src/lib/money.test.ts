import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatCents, parseInput, runningBalances, sumCents, toCents } from './money.ts';

test('parses German input', () => {
  assert.equal(parseInput('1.234,50'), '1234.50');
  assert.equal(parseInput('12,-'), '12.00');
  assert.equal(parseInput('12.5'), '12.50');
  assert.equal(parseInput('1.234'), '1234.00');
  assert.equal(parseInput(' 45 € '), '45.00');
  assert.equal(parseInput(''), null);
  assert.equal(parseInput('abc'), undefined);
});

test('formats cents', () => {
  assert.equal(formatCents(123450), '1.234,50');
  assert.equal(formatCents(5), '0,05');
  assert.equal(formatCents(-2000), '−20,00');
});

test('sums without float errors', () => {
  // 0.1 + 0.2 wäre mit float 0.30000000000000004
  assert.equal(sumCents(['0.10', '0.20', null]), 30);
  assert.equal(toCents('-12.30'), -1230);
});

test('negative values only when allowed', () => {
  assert.equal(parseInput('-50,00'), undefined);
  assert.equal(parseInput('-50,00', { allowNegative: true }), '-50.00');
  assert.equal(parseInput('−1.234,5', { allowNegative: true }), '-1234.50');
  assert.equal(parseInput('-', { allowNegative: true }), undefined);
});

test('running balance helper', () => {
  assert.deepEqual(runningBalances(10000, [['100.00', '30.00'], [null, null], [null, '200.00']]), [
    17000, 17000, -3000,
  ]);
});
