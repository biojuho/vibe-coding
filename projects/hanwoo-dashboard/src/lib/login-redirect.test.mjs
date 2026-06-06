import assert from "node:assert/strict";
import test from "node:test";
import { getSafeLoginRedirectTarget } from "./login-redirect.mjs";

test("getSafeLoginRedirectTarget returns same-origin protected callbacks", () => {
	assert.equal(
		getSafeLoginRedirectTarget(
			"http://127.0.0.1:3001/login?callbackUrl=http%3A%2F%2F127.0.0.1%3A3001%2Fsubscription%2Fsuccess",
		),
		"/subscription/success",
	);
	assert.equal(
		getSafeLoginRedirectTarget(
			"http://127.0.0.1:3001/login?callbackUrl=%2Fadmin%2Fdiagnostics%3Ftab%3Dhealth%23db",
		),
		"/admin/diagnostics?tab=health#db",
	);
});

test("getSafeLoginRedirectTarget rejects unsafe callbacks", () => {
	assert.equal(
		getSafeLoginRedirectTarget(
			"http://127.0.0.1:3001/login?callbackUrl=https%3A%2F%2Fevil.example%2Fsubscription",
		),
		"/",
	);
	assert.equal(
		getSafeLoginRedirectTarget(
			"http://127.0.0.1:3001/login?callbackUrl=%2Flogin%3FcallbackUrl%3D%252Fadmin",
		),
		"/",
	);
	assert.equal(
		getSafeLoginRedirectTarget("http://127.0.0.1:3001/login?callbackUrl=%2Fapi%2Fauth%2Fsession"),
		"/",
	);
	assert.equal(
		getSafeLoginRedirectTarget("http://127.0.0.1:3001/login?callbackUrl=%2F_next%2Fstatic%2Fchunk.js"),
		"/",
	);
	assert.equal(getSafeLoginRedirectTarget("not a url"), "/");
	assert.equal(getSafeLoginRedirectTarget("http://127.0.0.1:3001/login"), "/");
});
