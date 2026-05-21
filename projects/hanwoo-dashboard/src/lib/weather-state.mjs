export const WEATHER_UNAVAILABLE_MESSAGE =
  '지금은 날씨 데이터를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.';

export const WEATHER_STALE_MESSAGE =
  '실시간 날씨를 불러오지 못해 마지막으로 확인한 날씨 정보를 표시합니다.';

export const WEATHER_PARTIAL_MESSAGE =
  '일부 예보 데이터를 불러오지 못해 현재 날씨와 확인된 예보만 표시합니다.';

export const WEATHER_TIMEOUT_MESSAGE =
  '날씨 조회가 5초 안에 끝나지 않았습니다.';

function toNumberOrNull(value) {
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function normalizeForecast(daily) {
  const time = Array.isArray(daily?.time) ? daily.time : [];
  const codes = Array.isArray(daily?.weather_code) ? daily.weather_code : [];
  const tempMax = Array.isArray(daily?.temperature_2m_max) ? daily.temperature_2m_max : [];
  const tempMin = Array.isArray(daily?.temperature_2m_min) ? daily.temperature_2m_min : [];
  const precip = Array.isArray(daily?.precipitation_probability_max)
    ? daily.precipitation_probability_max
    : [];

  let degraded = time.length === 0;
  const forecast = [];

  time.forEach((date, index) => {
    const nextDate = isNonEmptyString(date) ? date : null;
    const nextCode = toNumberOrNull(codes[index]);
    const nextTempMax = toNumberOrNull(tempMax[index]);
    const nextTempMin = toNumberOrNull(tempMin[index]);
    const nextPrecip = toNumberOrNull(precip[index]) ?? 0;

    if (!nextDate || nextCode === null || nextTempMax === null || nextTempMin === null) {
      degraded = true;
      return;
    }

    forecast.push({
      date: nextDate,
      weatherCode: nextCode,
      tempMax: nextTempMax,
      tempMin: nextTempMin,
      precipProb: nextPrecip,
    });
  });

  return { forecast, degraded };
}

export async function readWeatherApiResponseSafely(response) {
  const rawText = await response.text();

  if (!rawText.trim()) {
    return {
      data: null,
      rawText,
      parseError: null,
    };
  }

  try {
    return {
      data: JSON.parse(rawText),
      rawText,
      parseError: null,
    };
  } catch (error) {
    return {
      data: null,
      rawText,
      parseError: error,
    };
  }
}

export function normalizeWeatherPayload(payload, options = {}) {
  const current = payload?.current;
  const temp = toNumberOrNull(current?.temperature_2m);
  const humidity = toNumberOrNull(current?.relative_humidity_2m);
  const windSpeed = toNumberOrNull(current?.wind_speed_10m);
  const apparentTemp = toNumberOrNull(current?.apparent_temperature);
  const weatherCode = toNumberOrNull(current?.weather_code);

  if (
    temp === null ||
    humidity === null ||
    windSpeed === null ||
    apparentTemp === null ||
    weatherCode === null
  ) {
    return null;
  }

  const { forecast, degraded } = normalizeForecast(payload?.daily);

  return {
    available: true,
    degraded,
    isStale: false,
    source: degraded ? 'weather-partial' : 'weather-live',
    sourceLabel: degraded ? '부분 예보' : '실시간 Open-Meteo',
    message: degraded ? WEATHER_PARTIAL_MESSAGE : null,
    temp,
    humidity,
    windSpeed,
    apparentTemp,
    weatherCode,
    tempMax: forecast[0]?.tempMax ?? temp + 3,
    tempMin: forecast[0]?.tempMin ?? temp - 3,
    precipitation: forecast[0]?.precipProb ?? 0,
    locationName: options.locationName ?? '서울',
    forecast,
  };
}

export function buildUnavailableWeatherState(options = {}) {
  return {
    available: false,
    degraded: true,
    isStale: true,
    source: 'weather-unavailable',
    sourceLabel: '확인 불가',
    message: options.message ?? WEATHER_UNAVAILABLE_MESSAGE,
    locationName: options.locationName ?? '서울',
    forecast: [],
  };
}

export function markWeatherAsStale(previousWeather, options = {}) {
  if (!previousWeather?.available) {
    return buildUnavailableWeatherState(options);
  }

  return {
    ...previousWeather,
    degraded: true,
    isStale: true,
    source: 'weather-stale',
    sourceLabel: '이전 날씨',
    locationName: options.locationName ?? previousWeather.locationName ?? '서울',
    message: options.message ?? WEATHER_STALE_MESSAGE,
  };
}
