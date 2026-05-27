"use client";

import { useEffect, useState } from "react";
import { fetchWithTimeout, isTimeoutError } from "@/lib/fetchWithTimeout";
import {
	buildUnavailableWeatherState,
	markWeatherAsStale,
	normalizeWeatherPayload,
	readWeatherApiResponseSafely,
	WEATHER_STALE_MESSAGE,
	WEATHER_TIMEOUT_MESSAGE,
	WEATHER_UNAVAILABLE_MESSAGE,
} from "@/lib/weather-state.mjs";

const FALLBACK_WEATHER_COORDS = { latitude: 35.446, longitude: 127.344 };

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
			const locationName = farmSettings?.location || "서울";

			try {
				const params = [
					`latitude=${lat}`,
					`longitude=${lng}`,
					"current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature",
					"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
					"forecast_days=3",
					"timezone=Asia/Seoul",
				].join("&");

				const res = await fetchWithTimeout(
					`https://api.open-meteo.com/v1/forecast?${params}`,
					{ cache: "no-store" },
					{
						timeoutMs: 5000,
						errorMessage: WEATHER_TIMEOUT_MESSAGE,
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
					applyWeatherDegradation(locationName, WEATHER_STALE_MESSAGE);
					return;
				}
				console.error("Weather fetch error", error);
				applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
			}
		};

		const fetchFallbackWeather = () => {
			fetchWeather(
				FALLBACK_WEATHER_COORDS.latitude,
				FALLBACK_WEATHER_COORDS.longitude,
			);
		};

		const fetchWeatherFromCoords = (latitudeValue, longitudeValue) => {
			const latitude = Number(latitudeValue);
			const longitude = Number(longitudeValue);
			const isValidWeatherCoordinate =
				Number.isFinite(latitude) &&
				Number.isFinite(longitude) &&
				latitude >= -90 &&
				latitude <= 90 &&
				longitude >= -180 &&
				longitude <= 180;

			if (isValidWeatherCoordinate) {
				fetchWeather(latitude, longitude);
				return true;
			}

			return false;
		};

		const fetchWeatherFromPosition = (position) => {
			if (fetchWeatherFromCoords(position?.coords?.latitude, position?.coords?.longitude)) {
				return;
			}

			fetchFallbackWeather();
		};

		if (farmSettings?.latitude && farmSettings?.longitude) {
			if (!fetchWeatherFromCoords(farmSettings.latitude, farmSettings.longitude)) {
				fetchFallbackWeather();
			}
		} else if (typeof navigator !== "undefined" && "geolocation" in navigator) {
			try {
				navigator.geolocation.getCurrentPosition(
					fetchWeatherFromPosition,
					fetchFallbackWeather,
				);
			} catch {
				fetchFallbackWeather();
			}
		} else {
			fetchFallbackWeather();
		}

		return () => {
			cancelled = true;
		};
	}, [farmSettings?.latitude, farmSettings?.longitude, farmSettings?.location]);

	return weather;
}
