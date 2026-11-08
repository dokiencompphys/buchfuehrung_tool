import assert from 'node:assert/strict';
import { test } from 'node:test';

import { daysOf, findIssues, type PhotoFacts } from './checks.ts';

const none: PhotoFacts = {
  opening: null,
  balances: {},
  totalIncome: null,
  totalExpense: null,
  closing: null,
  suspects: [],
};

// Foto: Übertrag 1.000,00; 2.: +100 → 1.100; 3.: −25 → 1.075; 4.: −5 → 1.070
const photo: PhotoFacts = {
  ...none,
  opening: 100000,
  balances: { 2: 110000, 3: 107500, 4: 107000 },
  totalIncome: 10000,
  totalExpense: 3000,
  closing: 107000,
};
const correct = [
  { day: 1, income: 0, expense: 0 },
  { day: 2, income: 10000, expense: 0 },
  { day: 3, income: 0, expense: 2500 },
  { day: 4, income: 0, expense: 500 },
];

test('no issues when everything adds up', () => {
  assert.deepEqual(findIssues(photo, correct, 100000), []);
});

test('nothing to compare without saldo or totals on the photo', () => {
  assert.deepEqual(findIssues(none, correct, 0), []);
});

test('misread amount is pinned to its row, later rows stay fine', () => {
  // 3.: 25,00 als 85,00 gelesen
  const days = correct.map((d) => (d.day === 3 ? { ...d, expense: 8500 } : d));
  const issues = findIssues(photo, days, 100000);
  const balance = issues.filter((i) => i.kind === 'balance');
  assert.deepEqual(balance, [{ id: 'balance:3', kind: 'balance', from: 3, to: 3, photo: 107500, computed: 101500 }]);
  assert.deepEqual(
    issues.filter((i) => i.kind === 'total').map((i) => i.id),
    ['total:expense'],
  );
  assert.deepEqual(daysOf(balance[0]), [3]);
});

test('rows without saldo on the photo are checked together with the next one', () => {
  const sparse: PhotoFacts = { ...photo, balances: { 4: 107000 }, totalIncome: null, totalExpense: null };
  const days = correct.map((d) => (d.day === 2 ? { ...d, income: 1000 } : d)); // 100,00 als 10,00
  const [issue] = findIssues(sparse, days, 100000);
  assert.equal(issue.kind, 'balance');
  assert.deepEqual(daysOf(issue), [1, 2, 3, 4]);
});

test('opening on the photo differs from the carried-over balance', () => {
  // Vormonat endete bei 1.050,00, auf dem Foto steht 1.000,00
  const issues = findIssues(photo, correct, 105000);
  assert.deepEqual(issues, [{ id: 'opening', kind: 'opening', photo: 100000, used: 105000 }]);
});

test('closing in the total row is checked', () => {
  const issues = findIssues({ ...photo, closing: 108000 }, correct, 100000);
  assert.deepEqual(issues, [{ id: 'closing', kind: 'closing', photo: 108000, computed: 107000 }]);
});

test('suspect cells from the photo are reported', () => {
  const suspects: PhotoFacts['suspects'] = [
    { day: 4, field: 'expense', reason: 'struck', read: [1250, 500], struck: [1250] },
  ];
  const [issue] = findIssues({ ...photo, suspects }, correct, 100000);
  assert.equal(issue.id, 'suspect:4:expense');
  assert.deepEqual(daysOf(issue), [4]);
});
