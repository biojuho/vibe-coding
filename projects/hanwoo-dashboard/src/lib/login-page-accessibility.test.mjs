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

test("login page has semantic main landmark with skip-link target id", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /<main className="login-shell" id="main-content">/);
	assert.match(source, /<\/main>/);
	assert.doesNotMatch(source, /<main className="login-shell">/);
});

test("login page form has password Eye/EyeOff toggle with aria-pressed", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /import \{[\s\S]*?Eye[\s\S]*?EyeOff[\s\S]*?\} from ["']lucide-react["']/);
	assert.match(source, /const \[showPassword, setShowPassword\] = useState\(false\)/);
	assert.match(source, /type=\{showPassword \? ["']text["'] : ["']password["']\}/);
	assert.match(source, /aria-pressed=\{showPassword\}/);
	assert.match(source, /const passwordToggleLabel = showPassword \? ["']비밀번호 숨기기["'] : ["']비밀번호 보기["']/);
	assert.match(source, /aria-label=\{passwordToggleLabel\}/);
	assert.match(source, /<EyeOff[\s\S]*?aria-hidden="true"/);
	assert.match(source, /<Eye[\s\S]*?aria-hidden="true"/);
});

test("login page submit button has aria-busy and dynamic accessible label", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /aria-busy=\{isSubmitting\}/);
	assert.match(source, /const loginSubmitLabel = isSubmitting/);
	assert.match(source, /aria-label=\{loginSubmitLabel\}/);
	assert.match(source, /disabled=\{!canSubmit\}/);
});

test("login page error message uses role=alert for immediate screen reader announcement", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /role="alert"/);
	assert.match(source, /const loginErrorId = ["']login-error-message["']/);
	assert.match(source, /id=\{loginErrorId\}/);
	assert.match(source, /aria-describedby=\{error \? loginErrorId : undefined\}/);
	assert.match(source, /아이디 또는 비밀번호를 다시 확인해 주세요/);
});

test("login page shows registration success banner on registered=1 param", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /params\.get\(["']registered["']\) === ["']1["']/);
	assert.match(source, /setRegistrationSuccess\(true\)/);
	assert.match(source, /\{registrationSuccess && \(/);
	assert.match(source, /role="status"/);
	assert.match(source, /계정이 만들어졌습니다/);
});

test("login page has legal links with accessible labels and legal redirect preservation", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /LOGIN_LEGAL_LINKS/);
	assert.match(source, /이용약관/);
	assert.match(source, /개인정보처리방침/);
	assert.match(source, /function buildLoginLegalDocumentHref\(/);
	assert.match(source, /aria-label=\{accessibleLabel\}/);
	assert.match(source, /title=\{accessibleLabel\}/);
	assert.match(source, /Joolife 이용약관 보기/);
	assert.match(source, /Joolife 개인정보처리방침 보기/);
});

test("login page username and password inputs are properly labelled and cross-referenced", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /const usernameInputId = ["']login-username["']/);
	assert.match(source, /const passwordInputId = ["']login-password["']/);
	assert.match(source, /htmlFor=\{usernameInputId\}/);
	assert.match(source, /htmlFor=\{passwordInputId\}/);
	assert.match(source, /id=\{usernameInputId\}/);
	assert.match(source, /id=\{passwordInputId\}/);
	assert.match(source, /autoComplete="username"/);
	assert.match(source, /autoComplete="current-password"/);
});

test("register page external links declare new-tab opening for screen readers", () => {
	const source = readSource("app/register/page.js");

	// Terms and privacy links open in a new tab — aria-label must tell screen reader users
	assert.match(source, /aria-label="이용약관 \(새 탭에서 열림\)"/);
	assert.match(source, /aria-label="개인정보처리방침 \(새 탭에서 열림\)"/);
	// Both must have noopener security attribute
	assert.match(source, /rel="noopener noreferrer"/);
});

test("register form links password mismatch error to input via aria-describedby", () => {
	const source = readSource("app/register/page.js");

	// Confirm input must have aria-describedby pointing to the mismatch error
	assert.match(source, /aria-describedby=\{passwordMismatch \? ["']reg-confirm-error["'] : undefined\}/);
	// Error paragraph must have matching id and role for screen reader announcement
	assert.match(source, /id="reg-confirm-error"/);
	assert.match(source, /role="alert"/);
	// Confirm input must still declare aria-invalid for state signaling
	assert.match(source, /aria-invalid=\{passwordMismatch\}/);
});

test("login form marks both username and password inputs as aria-required for screen readers", () => {
	const source = readSource("app/login/page.js");
	// WCAG 4.1.2: required fields must expose required state programmatically
	// Both fields are required for login — screen readers should announce this
	const requiredCount = (source.match(/aria-required="true"/g) || []).length;
	assert.ok(requiredCount >= 2, `Expected ≥2 aria-required="true" on login form, found ${requiredCount}`);

	// Verify on specific fields: aria-required must appear before aria-invalid for each
	const usernameNameIdx = source.indexOf('name="username"');
	const passwordNameIdx = source.indexOf('name="password"');
	const usernameAriaRequired = source.indexOf('aria-required="true"', usernameNameIdx);
	const usernameAriaInvalid = source.indexOf('aria-invalid=', usernameNameIdx);
	const passwordAriaRequired = source.indexOf('aria-required="true"', passwordNameIdx);
	const passwordAriaInvalid = source.indexOf('aria-invalid=', passwordNameIdx);

	assert.ok(usernameAriaRequired !== -1 && usernameAriaRequired < usernameAriaInvalid, "username: aria-required missing or after aria-invalid");
	assert.ok(passwordAriaRequired !== -1 && passwordAriaRequired < passwordAriaInvalid, "password: aria-required missing or after aria-invalid");
});
