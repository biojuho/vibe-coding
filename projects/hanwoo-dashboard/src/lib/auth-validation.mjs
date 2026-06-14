export const MIN_USERNAME_LENGTH = 3;
export const MAX_USERNAME_LENGTH = 30;
export const MIN_PASSWORD_LENGTH = 8;
// bcrypt silently truncates at 72 bytes; cap early to prevent DoS via long hashing
export const MAX_PASSWORD_LENGTH = 72;
export const USERNAME_PATTERN = /^[a-z0-9_]+$/;

export function validateRegistrationPayload(body) {
	const username =
		typeof body?.username === "string" ? body.username.trim() : "";
	const password = typeof body?.password === "string" ? body.password : "";

	if (
		username.length < MIN_USERNAME_LENGTH ||
		username.length > MAX_USERNAME_LENGTH
	) {
		return {
			error: `아이디는 ${MIN_USERNAME_LENGTH}~${MAX_USERNAME_LENGTH}자여야 합니다.`,
		};
	}
	if (!USERNAME_PATTERN.test(username)) {
		return {
			error: "아이디는 영문 소문자, 숫자, 밑줄(_)만 사용할 수 있습니다.",
		};
	}
	if (password.length < MIN_PASSWORD_LENGTH) {
		return {
			error: `비밀번호는 최소 ${MIN_PASSWORD_LENGTH}자 이상이어야 합니다.`,
		};
	}
	if (password.length > MAX_PASSWORD_LENGTH) {
		return {
			error: `비밀번호는 최대 ${MAX_PASSWORD_LENGTH}자까지 입력할 수 있습니다.`,
		};
	}

	return { username, password };
}

export function validateChangePasswordPayload(body) {
	const currentPassword =
		typeof body?.currentPassword === "string" ? body.currentPassword : "";
	const newPassword =
		typeof body?.newPassword === "string" ? body.newPassword : "";

	if (!currentPassword) {
		return { error: "현재 비밀번호를 입력해 주세요." };
	}
	if (newPassword.length < MIN_PASSWORD_LENGTH) {
		return {
			error: `새 비밀번호는 최소 ${MIN_PASSWORD_LENGTH}자 이상이어야 합니다.`,
		};
	}
	if (newPassword.length > MAX_PASSWORD_LENGTH) {
		return {
			error: `새 비밀번호는 최대 ${MAX_PASSWORD_LENGTH}자까지 입력할 수 있습니다.`,
		};
	}
	if (currentPassword === newPassword) {
		return { error: "새 비밀번호는 현재 비밀번호와 달라야 합니다." };
	}

	return { currentPassword, newPassword };
}
