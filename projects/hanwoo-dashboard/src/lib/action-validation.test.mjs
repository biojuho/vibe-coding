import assert from 'node:assert/strict';
import test from 'node:test';

import {
  validateCattleMutationInput,
  validateExpenseRecordInput,
  validateFarmSettingsInput,
  validateFeedRecordInput,
  validateInventoryItemInput,
  validateInventoryQuantityInput,
  validateSalesRecordInput,
} from './action-validation.mjs';

test('validateCattleMutationInput normalizes DB-facing cattle payloads', () => {
  const result = validateCattleMutationInput({
    name: '  해피  ',
    tagNumber: ' 123-456 ',
    buildingId: 'building-1',
    penNumber: '7',
    gender: '암',
    birthDate: '2024-01-15',
    status: '송아지',
    weight: '215.4',
    geneticInfo: {
      father: ' KPN-001 ',
      mother: '',
      grade: ' 1++ ',
    },
    memo: ' ',
    lastEstrus: '',
    pregnancyDate: null,
    purchasePrice: '1500000',
    purchaseDate: '2024-02-01',
  });

  assert.equal(result.success, true);
  assert.equal(result.data.name, '해피');
  assert.equal(result.data.tagNumber, '123-456');
  assert.equal(result.data.penNumber, 7);
  assert.equal(result.data.weight, 215.4);
  assert.equal(result.data.memo, '');
  assert.equal(result.data.geneticInfo.father, 'KPN-001');
  assert.equal(result.data.geneticInfo.mother, null);
  assert.equal(result.data.geneticInfo.grade, '1++');
  assert.equal(result.data.lastEstrus, null);
  assert.equal(result.data.pregnancyDate, null);
  assert.equal(result.data.purchasePrice, 1500000);
  assert.ok(result.data.birthDate instanceof Date);
  assert.ok(result.data.purchaseDate instanceof Date);
});

test('validateCattleMutationInput rejects invalid dates and non-numeric fields', () => {
  const result = validateCattleMutationInput({
    name: '테스트',
    tagNumber: '123',
    buildingId: 'building-1',
    penNumber: '0',
    gender: '암',
    birthDate: 'not-a-date',
    status: '송아지',
    weight: 'heavy',
  });

  assert.equal(result.success, false);
  assert.ok(result.validationErrors.penNumber?.length);
  assert.ok(result.validationErrors.birthDate?.length);
  assert.ok(result.validationErrors.weight?.length);
});

test('validateSalesRecordInput enforces required cattle linkage and price coercion', () => {
  const result = validateSalesRecordInput({
    saleDate: '2026-04-01',
    price: '9900000',
    cattleId: 'cattle-1',
    purchaser: '  남원축협 ',
    grade: '1+',
  });

  assert.equal(result.success, true);
  assert.equal(result.data.price, 9900000);
  assert.equal(result.data.purchaser, '남원축협');
});

test('validateSalesRecordInput rejects malformed sales payloads', () => {
  const result = validateSalesRecordInput({
    saleDate: '2026-04-01',
    price: 'abc',
    cattleId: '',
    grade: '9',
  });

  assert.equal(result.success, false);
  assert.ok(result.validationErrors.price?.length);
  assert.ok(result.validationErrors.cattleId?.length);
  assert.ok(result.validationErrors.grade?.length);
});

test('validateFeedRecordInput normalizes optional pen and note fields', () => {
  const result = validateFeedRecordInput({
    date: '2026-04-02',
    buildingId: 'building-2',
    penNumber: '',
    roughage: '18.5',
    concentrate: '7.25',
    note: ' ',
  });

  assert.equal(result.success, true);
  assert.equal(result.data.penNumber, null);
  assert.equal(result.data.note, null);
  assert.equal(result.data.roughage, 18.5);
  assert.equal(result.data.concentrate, 7.25);
});

test('validateInventoryItemInput rejects invalid categories and normalizes threshold', () => {
  const invalid = validateInventoryItemInput({
    name: '볏짚',
    category: 'Unknown',
    quantity: '10',
    unit: 'kg',
  });

  assert.equal(invalid.success, false);
  assert.ok(invalid.validationErrors.category?.length);

  const valid = validateInventoryItemInput({
    name: '볏짚',
    category: 'Feed',
    quantity: '10',
    unit: 'kg',
    threshold: '',
  });

  assert.equal(valid.success, true);
  assert.equal(valid.data.threshold, null);
});

test('validateFarmSettingsInput rejects out-of-range coordinates', () => {
  const result = validateFarmSettingsInput({
    name: '주라이프 농장',
    location: '남원',
    latitude: '200',
    longitude: '127.3',
  });

  assert.equal(result.success, false);
  assert.ok(result.validationErrors.latitude?.length);
});

test('validateExpenseRecordInput normalizes optional links and blocks invalid amounts', () => {
  const invalid = validateExpenseRecordInput({
    date: '2026-04-02',
    category: '',
    amount: '0',
  });

  assert.equal(invalid.success, false);
  assert.ok(invalid.validationErrors.category?.length);
  assert.ok(invalid.validationErrors.amount?.length);

  const valid = validateExpenseRecordInput({
    date: '2026-04-02',
    category: 'feed',
    amount: '120000',
    cattleId: '',
    buildingId: null,
    description: ' ',
  });

  assert.equal(valid.success, true);
  assert.equal(valid.data.cattleId, null);
  assert.equal(valid.data.buildingId, null);
  assert.equal(valid.data.description, null);
  assert.equal(valid.data.amount, 120000);
});

test('validateInventoryQuantityInput blocks negative quantities', () => {
  const invalid = validateInventoryQuantityInput('-1');
  assert.equal(invalid.success, false);
  assert.ok(invalid.validationErrors.quantity?.length);

  const valid = validateInventoryQuantityInput('0');
  assert.equal(valid.success, true);
  assert.equal(valid.data.quantity, 0);
});
