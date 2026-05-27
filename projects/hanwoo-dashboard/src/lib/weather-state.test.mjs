import assert from "node:assert/strict";
import test from "node:test";

import {
	buildUnavailableWeatherState,
	markWeatherAsStale,
	normalizeWeatherPayload,
	readWeatherApiResponseSafely,
	WEATHER_PARTIAL_MESSAGE,
	WEATHER_STALE_MESSAGE,
	WEATHER_UNAVAILABLE_MESSAGE,
} from "./weather-state.mjs";

test("readWeatherApiResponseSafely parses valid JSON payloads", async () => {
	const response = new Response(
		JSON.stringify({
			current: { temperature_2m: 18 },
		}),
		{ status: 200, headers: { "Content-Type": "application/json" } },
	);

	const result = await readWeatherApiResponseSafely(response);

	assert.equal(result.parseError, null);
	assert.equal(result.data.current.temperature_2m, 18);
});

test("readWeatherApiResponseSafely captures malformed JSON without throwing", async () => {
	const response = new Response('{"current":', {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});

	const result = await readWeatherApiResponseSafely(response);

	assert.equal(result.data, null);
	assert.ok(result.parseError instanceof SyntaxError);
});

test("normalizeWeatherPayload normalizes a valid Open-Meteo response", () => {
	const result = normalizeWeatherPayload(
		{
			current: {
				temperature_2m: 20.4,
				relative_humidity_2m: 61,
				weather_code: 2,
				wind_speed_10m: 3.2,
				apparent_temperature: 19.7,
			},
			daily: {
				time: ["2026-04-07", "2026-04-08"],
				weather_code: [2, 61],
				temperature_2m_max: [24.1, 21.2],
				temperature_2m_min: [12.8, 10.1],
				precipitation_probability_max: [10, 80],
			},
		},
		{ locationName: "Namwon" },
	);

	assert.equal(result.available, true);
	assert.equal(result.degraded, false);
	assert.equal(result.sourceLabel, "실시간 Open-Meteo");
	assert.equal(result.locationName, "Namwon");
	assert.equal(result.forecast.length, 2);
	assert.equal(result.tempMax, 24.1);
});

test("normalizeWeatherPayload degrades cleanly when forecast arrays are partial", () => {
	const result = normalizeWeatherPayload({
		current: {
			temperature_2m: 20,
			relative_humidity_2m: 55,
			weather_code: 1,
			wind_speed_10m: 2,
			apparent_temperature: 19,
		},
		daily: {
			time: ["2026-04-07", "2026-04-08"],
			weather_code: [1],
			temperature_2m_max: [23, 21],
			temperature_2m_min: [14, 12],
			precipitation_probability_max: [0, 20],
		},
	});

	assert.equal(result.available, true);
	assert.equal(result.degraded, true);
	assert.equal(result.sourceLabel, "부분 예보");
	assert.equal(result.message, WEATHER_PARTIAL_MESSAGE);
	assert.match(result.message, /일부 예보 정보를 불러오지 못해/);
	assert.doesNotMatch(result.message, /일부 예보 데이터를 불러오지 못해/);
	assert.equal(result.forecast.length, 1);
	assert.equal(result.precipitation, 0);
	assert.equal(result.locationName, "서울");
});

test("normalizeWeatherPayload returns null when required current fields are missing", () => {
	const result = normalizeWeatherPayload({
		current: {
			temperature_2m: 20,
			relative_humidity_2m: 55,
			weather_code: 1,
			wind_speed_10m: 2,
		},
	});

	assert.equal(result, null);
});

test("markWeatherAsStale preserves the last snapshot while surfacing a degraded state", () => {
	const result = markWeatherAsStale({
		available: true,
		degraded: false,
		isStale: false,
		source: "weather-live",
		sourceLabel: "Open-Meteo",
		temp: 20,
		humidity: 55,
		windSpeed: 2,
		apparentTemp: 19,
		weatherCode: 1,
		tempMax: 23,
		tempMin: 14,
		precipitation: 0,
		locationName: "Namwon",
		forecast: [],
	});

	assert.equal(result.degraded, true);
	assert.equal(result.isStale, true);
	assert.equal(result.source, "weather-stale");
	assert.equal(result.sourceLabel, "이전 날씨");
	assert.equal(result.message, WEATHER_STALE_MESSAGE);
});

test("buildUnavailableWeatherState returns an explicit unavailable payload", () => {
	const result = buildUnavailableWeatherState({ locationName: "Namwon" });

	assert.equal(result.available, false);
	assert.equal(result.locationName, "Namwon");
	assert.equal(result.sourceLabel, "날씨 확인 불가");
	assert.equal(result.message, WEATHER_UNAVAILABLE_MESSAGE);
	assert.match(result.message, /날씨 정보를 확인할 수 없습니다/);
	assert.doesNotMatch(result.message, /날씨 데이터를 확인할 수 없습니다/);
});

test("weather fallback location labels default to Korean copy", () => {
	const unavailable = buildUnavailableWeatherState();
	const stale = markWeatherAsStale({
		available: true,
		degraded: false,
		isStale: false,
		source: "weather-live",
		sourceLabel: "실시간 Open-Meteo",
		temp: 20,
		humidity: 55,
		windSpeed: 2,
		apparentTemp: 19,
		weatherCode: 1,
		tempMax: 23,
		tempMin: 14,
		precipitation: 0,
		forecast: [],
	});

	assert.equal(unavailable.locationName, "서울");
	assert.equal(stale.locationName, "서울");
	assert.notEqual(unavailable.locationName, "Seoul");
	assert.notEqual(stale.locationName, "Seoul");
});

test("weather degraded-state copy avoids English placeholder labels", () => {
	const unavailable = buildUnavailableWeatherState({ locationName: "Namwon" });
	const stale = markWeatherAsStale({
		available: true,
		degraded: false,
		isStale: false,
		source: "weather-live",
		sourceLabel: "Open-Meteo",
		temp: 20,
		humidity: 55,
		windSpeed: 2,
		apparentTemp: 19,
		weatherCode: 1,
		tempMax: 23,
		tempMin: 14,
		precipitation: 0,
		locationName: "Namwon",
		forecast: [],
	});
	const partial = normalizeWeatherPayload({
		current: {
			temperature_2m: 20,
			relative_humidity_2m: 55,
			weather_code: 1,
			wind_speed_10m: 2,
			apparent_temperature: 19,
		},
		daily: {
			time: ["2026-04-07", "2026-04-08"],
			weather_code: [1],
			temperature_2m_max: [23, 21],
			temperature_2m_min: [14, 12],
			precipitation_probability_max: [0, 20],
		},
	});

	const visibleCopy = [
		unavailable.sourceLabel,
		unavailable.message,
		stale.sourceLabel,
		stale.message,
		partial.sourceLabel,
		partial.message,
	].join(" ");

	assert.doesNotMatch(
		visibleCopy,
		/Weather data|temporarily unavailable|Stale Weather|Partial Forecast|Unavailable/,
	);
});
