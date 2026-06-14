import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

const source = readSource("lib/audio.js");

test("audio exports all 5 public APIs", () => {
	const apis = [
		"playTactileClick",
		"playScanSuccess",
		"playScanFailure",
		"triggerVibration",
		"playTriumphantChime",
	];
	for (const api of apis) {
		assert.ok(source.includes(api), `Missing export: ${api}`);
	}
});

test("audio getAudioContext is SSR-safe via typeof window check", () => {
	assert.match(source, /typeof window === ["']undefined["']/);
	// Must return null early in non-browser env
	assert.match(source, /typeof window === ["']undefined["'] \? null : null|typeof window === ["']undefined["']\) return null/);
});

test("audio getAudioContext falls back to webkitAudioContext for Safari compatibility", () => {
	assert.match(source, /window\.AudioContext \|\| window\.webkitAudioContext/);
});

test("audio getAudioContext auto-resumes suspended audio context", () => {
	// autoplay policy may suspend the context — must resume on interaction
	assert.match(source, /audioCtx\.state === ["']suspended["']/);
	assert.match(source, /audioCtx\.resume\(\)/);
});

test("audio getAudioContext swallows resume promise rejection silently", () => {
	// Promise rejection must not be unhandled — void + .catch(() => {}) pattern
	assert.match(source, /\.catch\(\(\) => \{\}\)/);
	assert.match(source, /void resumeResult/);
});

test("audio playTactileClick uses sine oscillator with 150→80Hz frequency ramp", () => {
	assert.match(source, /playTactileClick/);
	assert.match(source, /osc\.type = ["']sine["']/);
	assert.match(source, /osc\.frequency\.setValueAtTime\(150,/);
	assert.match(source, /osc\.frequency\.exponentialRampToValueAtTime\(80,/);
});

test("audio playScanSuccess uses two-tone A5→A6 beep for positive feedback", () => {
	assert.match(source, /playScanSuccess/);
	// A5 = 880Hz, A6 = 1760Hz
	assert.match(source, /880,/);
	assert.match(source, /1760,/);
});

test("audio playScanFailure uses sawtooth waveform for error distinction", () => {
	assert.match(source, /playScanFailure/);
	assert.match(source, /osc\.type = ["']sawtooth["']/);
	// Descending frequency ramp signals failure
	assert.match(source, /osc\.frequency\.linearRampToValueAtTime\(120,/);
});

test("audio playTriumphantChime plays a C major chord arpeggio", () => {
	assert.match(source, /playTriumphantChime/);
	// C4=261.63, E4=329.63, G4=392.00, C5=523.25
	assert.match(source, /261\.63/);
	assert.match(source, /329\.63/);
	assert.match(source, /392\.0/);
	assert.match(source, /523\.25/);
	assert.match(source, /notes\.forEach/);
});

test("audio triggerVibration uses safe call pattern to avoid TypeError on some devices", () => {
	assert.match(source, /triggerVibration/);
	// Must call vibrate via .call(navigatorRef, ...) not navigator.vibrate() directly
	// to avoid TypeError on restricted environments
	assert.match(source, /vibrate\.call\(navigatorRef, duration\)/);
	// SSR guard
	assert.match(source, /typeof window === ["']undefined["']/);
});

test("audio functions catch all exceptions to avoid breaking the UI on audio failure", () => {
	// Each function wraps its audio API calls in try/catch
	const tryCatchCount = (source.match(/} catch/g) || []).length;
	// getAudioContext has 2 try/catch (context access + creation), plus each exported fn has 1
	assert.ok(tryCatchCount >= 6, `Expected ≥6 try/catch blocks, found ${tryCatchCount}`);
	assert.match(source, /console\.warn/);
});

test("audio reuses a single AudioContext instance across calls", () => {
	// Singleton pattern: audioCtx is a module-level variable
	assert.match(source, /let audioCtx = null/);
	assert.match(source, /if \(!audioCtx\)/);
});
