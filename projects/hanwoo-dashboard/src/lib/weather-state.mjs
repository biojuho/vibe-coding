export const WEATHER_UNAVAILABLE_MESSAGE =
  'Weather data is temporarily unavailable. Please retry shortly.';

export const WEATHER_STALE_MESSAGE =
  'Showing the last available weather snapshot because the live weather service is unavailable.';

export const WEATHER_PARTIAL_MESSAGE =
  'Showing current conditions with a reduced forecast because part of the weather feed was unavailable.';

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
    sourceLabel: degraded ? 'Partial Forecast' : 'Open-Meteo',
    message: degraded ? WEATHER_PARTIAL_MESSAGE : null,
    temp,
    humidity,
    windSpeed,
    apparentTemp,
    weatherCode,
    tempMax: forecast[0]?.tempMax ?? temp + 3,
    tempMin: forecast[0]?.tempMin ?? temp - 3,
    precipitation: forecast[0]?.precipProb ?? 0,
    locationName: options.locationName ?? 'Seoul',
    forecast,
  };
}

export function buildUnavailableWeatherState(options = {}) {
  return {
    available: false,
    degraded: true,
    isStale: true,
    source: 'weather-unavailable',
    sourceLabel: 'Unavailable',
    message: options.message ?? WEATHER_UNAVAILABLE_MESSAGE,
    locationName: options.locationName ?? 'Seoul',
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
    sourceLabel: 'Stale Weather',
    locationName: options.locationName ?? previousWeather.locationName ?? 'Seoul',
    message: options.message ?? WEATHER_STALE_MESSAGE,
  };
}
