import { z } from 'zod';

import { toInputDate } from '@/lib/utils';

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

const requiredText = (message, max = 100) =>
  z.string().trim().min(1, message).max(max, `${max}자 이하로 입력해 주세요.`);

const validDateString = (message) =>
  z
    .string()
    .min(1, message)
    .refine((value) => !Number.isNaN(new Date(value).getTime()), '올바른 날짜를 입력해 주세요.');

const optionalText = (max = 300) =>
  z.preprocess(emptyToUndefined, z.string().max(max, `${max}자 이하로 입력해 주세요.`).optional());

const optionalNumber = () =>
  z.preprocess(
    emptyToUndefined,
    z.coerce.number().nonnegative('0 이상 값을 입력해 주세요.').optional(),
  );

const optionalDate = () =>
  z.preprocess(
    emptyToUndefined,
    z
      .string()
      .refine((value) => !Number.isNaN(new Date(value).getTime()), '올바른 날짜를 입력해 주세요.')
      .optional(),
  );

export const cattleFormSchema = z.object({
  name: requiredText('개체 이름을 입력해 주세요.', 40),
  tagNumber: requiredText('이력번호를 입력해 주세요.', 30),
  buildingId: requiredText('축사를 선택해 주세요.', 40),
  penNumber: z.coerce.number().int().min(1, '칸 번호를 선택해 주세요.').max(99, '칸 번호를 확인해 주세요.'),
  gender: requiredText('성별을 선택해 주세요.', 10),
  birthDate: validDateString('생년월일을 입력해 주세요.'),
  status: requiredText('상태를 선택해 주세요.', 30),
  weight: z.coerce.number().positive('체중은 0보다 커야 합니다.'),
  geneticInfo: z.object({
    father: optionalText(50),
    mother: optionalText(50),
    grade: optionalText(20),
  }),
  memo: optionalText(500),
  purchasePrice: optionalNumber(),
  purchaseDate: optionalDate(),
});

export const scheduleEventSchema = z.object({
  title: requiredText('일정 제목을 입력해 주세요.', 120),
  date: validDateString('일정을 등록할 날짜를 선택해 주세요.'),
  type: z.enum(['General', 'Vaccination', 'Checkup', 'Breeding', 'Other']),
});

export const inventoryItemSchema = z.object({
  name: requiredText('자재 이름을 입력해 주세요.', 80),
  category: z.enum(['Feed', 'Medicine', 'Equipment', 'Other']),
  quantity: z.coerce.number().positive('수량은 0보다 커야 합니다.'),
  unit: requiredText('단위를 입력해 주세요.', 20),
  threshold: optionalNumber(),
});

export const salesFormSchema = z.object({
  saleDate: validDateString('출하 날짜를 선택해 주세요.'),
  price: z.coerce.number().positive('판매 가격은 0보다 커야 합니다.'),
  cattleId: requiredText('출하할 개체를 선택해 주세요.', 80),
  purchaser: optionalText(80),
  grade: z.enum(['1++', '1+', '1', '2', '3']),
  notes: optionalText(300),
});

export const feedRecordSchema = z.object({
  date: validDateString('급여 날짜를 선택해 주세요.'),
  roughage: z.coerce.number().positive('조사료 양은 0보다 커야 합니다.'),
  concentrate: z.coerce.number().positive('배합사료 양은 0보다 커야 합니다.'),
  note: optionalText(300),
});

export const calvingRecordSchema = z.object({
  calvingDate: validDateString('분만일을 입력해 주세요.'),
  calfGender: z.enum(['암', '수']),
});

export const buildingFormSchema = z.object({
  name: requiredText('동 이름을 입력해 주세요.', 40),
  penCount: z.coerce.number().int().min(1, '칸 수는 1 이상이어야 합니다.').max(200, '칸 수를 확인해 주세요.'),
});

export const farmSettingsSchema = z.object({
  name: requiredText('농장 이름을 입력해 주세요.', 60),
  location: requiredText('농장 위치를 입력해 주세요.', 80),
  latitude: z.coerce.number().min(-90, '위도를 확인해 주세요.').max(90, '위도를 확인해 주세요.'),
  longitude: z.coerce.number().min(-180, '경도를 확인해 주세요.').max(180, '경도를 확인해 주세요.'),
});

export function createCattleFormValues(cattle, buildings = []) {
  const defaultBuildingId = cattle?.buildingId ?? buildings[0]?.id ?? '';

  return {
    name: cattle?.name ?? '',
    tagNumber: cattle?.tagNumber ?? '',
    buildingId: defaultBuildingId,
    penNumber: cattle?.penNumber ?? 1,
    gender: cattle?.gender ?? '암',
    birthDate: cattle?.birthDate ? toInputDate(cattle.birthDate) : '',
    status: cattle?.status ?? '송아지',
    weight: cattle?.weight ?? '',
    geneticInfo: {
      father: cattle?.geneticInfo?.father ?? cattle?.geneticFather ?? '',
      mother: cattle?.geneticInfo?.mother ?? cattle?.geneticMother ?? '',
      grade: cattle?.geneticInfo?.grade ?? cattle?.geneticGrade ?? '-',
    },
    memo: cattle?.memo ?? '',
    purchasePrice: cattle?.purchasePrice ?? '',
    purchaseDate: cattle?.purchaseDate ? toInputDate(cattle.purchaseDate) : '',
  };
}

export function createScheduleFormValues(date = new Date()) {
  const baseDate = date instanceof Date ? date : new Date(date);

  return {
    title: '',
    date: baseDate.toISOString().split('T')[0],
    type: 'General',
  };
}

export function createInventoryFormValues() {
  return {
    name: '',
    category: 'Feed',
    quantity: '',
    unit: 'kg',
    threshold: '',
  };
}

export function createSalesFormValues() {
  return {
    saleDate: '',
    price: '',
    cattleId: '',
    purchaser: '',
    grade: '1',
    notes: '',
  };
}

export function createFeedRecordValues() {
  return {
    date: new Date().toISOString().split('T')[0],
    roughage: '',
    concentrate: '',
    note: '',
  };
}

export function createCalvingFormValues(date = new Date()) {
  return {
    calvingDate: toInputDate(date),
    calfGender: '암',
  };
}

export function createBuildingFormValues() {
  return {
    name: '',
    penCount: 32,
  };
}

export function createFarmSettingsValues(settings) {
  return {
    name: settings?.name ?? '',
    location: settings?.location ?? '',
    latitude: settings?.latitude ?? 35.446,
    longitude: settings?.longitude ?? 127.344,
  };
}
