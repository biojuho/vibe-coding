export const ESTRUS_CYCLE_DAYS = 21;
export const ESTRUS_ALERT_WINDOW = 3;
export const CALVING_DAYS = 285;
export const CALVING_ALERT_WINDOW = 14;
export const TODAY = new Date();

export const BREED_STATUS_OPTIONS = ['송아지', '육성우', '번식우', '임신우', '비육우', '씨수소'];

export const STATUS_COLORS = {
  송아지: { bg: '#f7ead9', text: '#8f5630', dot: '#c98a52' },
  육성우: { bg: '#e7efe3', text: '#5a734f', dot: '#7f9a76' },
  번식우: { bg: '#f7e3ea', text: '#96556f', dot: '#cf7f99' },
  임신우: { bg: '#efe7f6', text: '#776694', dot: '#a28cc0' },
  비육우: { bg: '#e4ebf3', text: '#5f7694', dot: '#88a0bc' },
  씨수소: { bg: '#eee5dc', text: '#6c594a', dot: '#9a816e' },
};

export const BUILDINGS = [
  { id: 'building_1', name: '1동', description: '번식우사', penCount: 32 },
  { id: 'building_2', name: '2동', description: '비육우사', penCount: 32 },
  { id: 'building_3', name: '3동', description: '육성우사', penCount: 32 },
];

export const NAMWON_LAT = 35.446;
export const NAMWON_LNG = 127.344;

export const FEED_STANDARDS = {
  송아지: {
    roughage: '건초',
    roughageKg: 1.5,
    concentrate: '송아지 전용',
    concentrateKg: 2.0,
    note: '이유 후 조사료 급여',
  },
  육성우: {
    roughage: '건초+볏짚',
    roughageKg: 4.0,
    concentrate: '육성우용',
    concentrateKg: 3.0,
    note: '조단백 15% 이상',
  },
  번식우: {
    roughage: '볏짚+건초',
    roughageKg: 5.0,
    concentrate: '번식우용',
    concentrateKg: 2.5,
    note: '체형 유지, 과비 주의',
  },
  임신우: {
    roughage: '양질건초',
    roughageKg: 5.5,
    concentrate: '번식우용',
    concentrateKg: 3.0,
    note: '분만 2개월 전 증량',
  },
  비육우: {
    roughage: '볏짚',
    roughageKg: 1.5,
    concentrate: '비육후기/전기',
    concentrateKg: 8.0,
    note: '마블링 향상을 위해 농후사료 비중 확대',
  },
  씨수소: {
    roughage: '건초+볏짚',
    roughageKg: 5.0,
    concentrate: '번식우용',
    concentrateKg: 3.5,
    note: '과비 방지, 운동 필수',
  },
};
