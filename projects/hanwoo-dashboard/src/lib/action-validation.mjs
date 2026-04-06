import { z } from 'zod';

const CATTLE_GENDERS = ['암', '수'];
const CATTLE_STATUSES = ['송아지', '육성우', '번식우', '임신우', '비육우', '씨수소'];
const SALES_GRADES = ['1++', '1+', '1', '2', '3'];
const INVENTORY_CATEGORIES = ['Feed', 'Medicine', 'Equipment', 'Other'];

const emptyToUndefined = (value) => {
  if (value === '' || value === null || value === undefined) {
    return undefined;
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed === '' ? undefined : trimmed;
  }

  return value;
};

const toNumber = (value) => {
  const normalized = emptyToUndefined(value);
  if (normalized === undefined) {
    return undefined;
  }

  if (typeof normalized === 'string' || typeof normalized === 'number') {
    return Number(normalized);
  }

  return normalized;
};

const toDate = (value) => {
  const normalized = emptyToUndefined(value);
  if (normalized === undefined) {
    return undefined;
  }

  if (normalized instanceof Date) {
    return normalized;
  }

  if (typeof normalized === 'string' || typeof normalized === 'number') {
    return new Date(normalized);
  }

  return normalized;
};

const requiredText = (message, max = 100) =>
  z.preprocess(
    emptyToUndefined,
    z.string().trim().min(1, message).max(max, `${max}자 이하로 입력해 주세요.`),
  );

const optionalText = (max = 300) =>
  z.preprocess(
    emptyToUndefined,
    z.string().trim().max(max, `${max}자 이하로 입력해 주세요.`).optional(),
  );

const boundedNumber = (message, { integer = false, positive = false, nonnegative = false, min, max } = {}) => {
  let schema = z.number().refine(Number.isFinite, message);

  if (integer) {
    schema = schema.int(message);
  }

  if (positive) {
    schema = schema.positive(message);
  } else if (nonnegative) {
    schema = schema.nonnegative(message);
  }

  if (min !== undefined) {
    schema = schema.min(min, message);
  }

  if (max !== undefined) {
    schema = schema.max(max, message);
  }

  return schema;
};

const requiredPositiveNumber = (message) =>
  z.preprocess(toNumber, boundedNumber(message, { positive: true }));

const requiredPositiveInt = (message, max) =>
  z.preprocess(toNumber, boundedNumber(message, { integer: true, positive: true, max }));

const optionalNonNegativeNumber = (message, max) =>
  z.preprocess(toNumber, boundedNumber(message, { nonnegative: true, max }).optional());

const optionalNonNegativeInt = (message, max) =>
  z.preprocess(toNumber, boundedNumber(message, { integer: true, nonnegative: true, max }).optional());

const requiredDate = (message) =>
  z.preprocess(
    toDate,
    z.date().refine((value) => !Number.isNaN(value.getTime()), message),
  );

const optionalDate = (message) =>
  z.preprocess(
    toDate,
    z.date().refine((value) => !Number.isNaN(value.getTime()), message).optional(),
  );

function buildValidationFailure(result, fallbackMessage) {
  const flattened = result.error.flatten();
  const firstFieldError = Object.values(flattened.fieldErrors).flat().find(Boolean);
  const firstFormError = flattened.formErrors.find(Boolean);

  return {
    success: false,
    message: firstFieldError ?? firstFormError ?? fallbackMessage,
    validationErrors: flattened.fieldErrors,
  };
}

function validateActionInput(schema, input, fallbackMessage = '입력값을 다시 확인해 주세요.') {
  const result = schema.safeParse(input);

  if (!result.success) {
    return buildValidationFailure(result, fallbackMessage);
  }

  return {
    success: true,
    data: result.data,
  };
}

const cattleMutationSchema = z
  .object({
    name: requiredText('개체 이름을 입력해 주세요.', 40),
    tagNumber: requiredText('이력번호를 입력해 주세요.', 30),
    buildingId: requiredText('축사를 선택해 주세요.', 80),
    penNumber: requiredPositiveInt('칸 번호를 확인해 주세요.', 99),
    gender: z.enum(CATTLE_GENDERS),
    birthDate: requiredDate('올바른 생년월일을 입력해 주세요.'),
    status: z.enum(CATTLE_STATUSES),
    weight: requiredPositiveNumber('체중은 0보다 커야 합니다.'),
    geneticInfo: z
      .object({
        father: optionalText(50),
        mother: optionalText(50),
        grade: optionalText(20),
      })
      .optional(),
    memo: optionalText(500),
    lastEstrus: optionalDate('올바른 발정일을 입력해 주세요.'),
    pregnancyDate: optionalDate('올바른 수정일을 입력해 주세요.'),
    purchasePrice: optionalNonNegativeInt('매입가는 0 이상이어야 합니다.'),
    purchaseDate: optionalDate('올바른 매입일을 입력해 주세요.'),
  })
  .transform((payload) => ({
    ...payload,
    memo: payload.memo ?? '',
    geneticInfo: {
      father: payload.geneticInfo?.father ?? null,
      mother: payload.geneticInfo?.mother ?? null,
      grade: payload.geneticInfo?.grade ?? null,
    },
    lastEstrus: payload.lastEstrus ?? null,
    pregnancyDate: payload.pregnancyDate ?? null,
    purchasePrice: payload.purchasePrice ?? null,
    purchaseDate: payload.purchaseDate ?? null,
  }));

const salesRecordSchema = z
  .object({
    saleDate: requiredDate('출하 날짜를 선택해 주세요.'),
    price: requiredPositiveInt('판매 금액은 0보다 커야 합니다.'),
    cattleId: requiredText('출하할 개체를 선택해 주세요.', 80),
    purchaser: optionalText(80),
    grade: z.enum(SALES_GRADES),
  })
  .transform((payload) => ({
    ...payload,
    purchaser: payload.purchaser ?? null,
  }));

const feedRecordSchema = z
  .object({
    date: requiredDate('급여 날짜를 선택해 주세요.'),
    buildingId: requiredText('축사를 선택해 주세요.', 80),
    penNumber: optionalNonNegativeInt('칸 번호를 확인해 주세요.', 99),
    roughage: requiredPositiveNumber('조사료량은 0보다 커야 합니다.'),
    concentrate: requiredPositiveNumber('배합사료량은 0보다 커야 합니다.'),
    note: optionalText(300),
  })
  .transform((payload) => ({
    ...payload,
    penNumber: payload.penNumber ?? null,
    note: payload.note ?? null,
  }));

const inventoryItemSchema = z
  .object({
    name: requiredText('자재 이름을 입력해 주세요.', 80),
    category: z.enum(INVENTORY_CATEGORIES),
    quantity: requiredPositiveNumber('수량은 0보다 커야 합니다.'),
    unit: requiredText('단위를 입력해 주세요.', 20),
    threshold: optionalNonNegativeNumber('기준 수량은 0 이상이어야 합니다.'),
  })
  .transform((payload) => ({
    ...payload,
    threshold: payload.threshold ?? null,
  }));

const farmSettingsSchema = z.object({
  name: requiredText('농장 이름을 입력해 주세요.', 60),
  location: requiredText('농장 위치를 입력해 주세요.', 80),
  latitude: z.preprocess(toNumber, boundedNumber('위도를 확인해 주세요.', { min: -90, max: 90 })),
  longitude: z.preprocess(toNumber, boundedNumber('경도를 확인해 주세요.', { min: -180, max: 180 })),
});

const expenseRecordSchema = z
  .object({
    date: requiredDate('지출 날짜를 선택해 주세요.'),
    cattleId: optionalText(80),
    buildingId: optionalText(80),
    category: requiredText('카테고리를 입력해 주세요.', 60),
    amount: requiredPositiveInt('지출 금액은 0보다 커야 합니다.'),
    description: optionalText(300),
  })
  .transform((payload) => ({
    ...payload,
    cattleId: payload.cattleId ?? null,
    buildingId: payload.buildingId ?? null,
    description: payload.description ?? null,
  }));

const inventoryQuantitySchema = z.object({
  quantity: z.preprocess(
    toNumber,
    boundedNumber('수량은 0 이상이어야 합니다.', { nonnegative: true }),
  ),
});

export function validateCattleMutationInput(input) {
  return validateActionInput(cattleMutationSchema, input);
}

export function validateSalesRecordInput(input) {
  return validateActionInput(salesRecordSchema, input);
}

export function validateFeedRecordInput(input) {
  return validateActionInput(feedRecordSchema, input);
}

export function validateInventoryItemInput(input) {
  return validateActionInput(inventoryItemSchema, input);
}

export function validateFarmSettingsInput(input) {
  return validateActionInput(farmSettingsSchema, input);
}

export function validateExpenseRecordInput(input) {
  return validateActionInput(expenseRecordSchema, input);
}

export function validateInventoryQuantityInput(quantity) {
  return validateActionInput(inventoryQuantitySchema, { quantity });
}
