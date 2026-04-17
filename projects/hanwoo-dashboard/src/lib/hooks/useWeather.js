'use client';

import { useState, useEffect } from 'react';
import { fetchWithTimeout, isTimeoutError } from '@/lib/fetchWithTimeout';
import {
  buildUnavailableWeatherState,
  markWeatherAsStale,
  normalizeWeatherPayload,
  readWeatherApiResponseSafely,
  WEATHER_UNAVAILABLE_MESSAGE,
} from '@/lib/weather-state.mjs';

export function useWeather(farmSettings) {
  const [weather, setWeather] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const applyWeatherDegradation = (locationName, message) => {
      if (cancelled) return;
      setWeather((previous) =>
        previous?.available
          ? markWeatherAsStale(previous, { locationName, message })
          : buildUnavailableWeatherState({ locationName, message }),
      );
    };

    const fetchWeather = async (lat, lng) => {
      const locationName = farmSettings?.location || 'Seoul';

      try {
        const params = [
          `latitude=${lat}`,
          `longitude=${lng}`,
          'current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature',
          'daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
          'forecast_days=3',
          'timezone=Asia/Seoul',
        ].join('&');
        
        const res = await fetchWithTimeout(
          `https://api.open-meteo.com/v1/forecast?${params}`,
          { cache: 'no-store' },
          {
            timeoutMs: 5000,
            errorMessage: 'Weather lookup timed out after 5000ms.',
          },
        );

        if (!res.ok) {
          applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
          return;
        }

        const { data, parseError } = await readWeatherApiResponseSafely(res);
        if (parseError) {
          applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
          return;
        }

        const normalized = normalizeWeatherPayload(data, { locationName });
        if (!normalized) {
          applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
          return;
        }

        if (!cancelled) {
          setWeather(normalized);
        }
      } catch (error) {
        if (isTimeoutError(error)) {
          applyWeatherDegradation(
            locationName,
            'Showing the last available weather snapshot because the live weather request timed out.',
          );
          return;
        }
        console.error('Weather fetch error', error);
        applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
      }
    };

    if (farmSettings?.latitude && farmSettings?.longitude) {
      fetchWeather(farmSettings.latitude, farmSettings.longitude);
    } else if (typeof navigator !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => fetchWeather(position.coords.latitude, position.coords.longitude),
        () => fetchWeather(35.446, 127.344),
      );
    } else {
      fetchWeather(35.446, 127.344);
    }

    return () => {
      cancelled = true;
    };
  }, [farmSettings?.latitude, farmSettings?.longitude, farmSettings?.location]);

  return weather;
}
