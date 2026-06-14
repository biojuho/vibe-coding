// Pre-computed bcrypt hash used only for timing equalization (cost=12, same as registration).
// When the username is not found we still call bcrypt.compare to prevent username enumeration
// via response-time differences (login attempts for unknown users are ~10× faster otherwise).
const TIMING_DUMMY_HASH =
	"$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGNSB3lCq2tCCfmMGgLkC1TLUYS";

function isPlainObject(value) {
	return (
		value !== null &&
		typeof value === "object" &&
		!Array.isArray(value)
	);
}

export async function authorizeCredentials(credentials, deps = {}) {
	const username =
		typeof credentials?.username === "string" ? credentials.username : "";
	const password =
		typeof credentials?.password === "string" ? credentials.password : "";

	if (!username || !password) {
		return null;
	}

	const safeDeps = isPlainObject(deps) ? deps : {};
	const loadPrisma =
		safeDeps.loadPrisma ?? (async () => (await import("@/lib/db")).default);
	const loadBcrypt =
		safeDeps.loadBcrypt ?? (async () => (await import("bcrypt")).default);

	try {
		const prisma = await loadPrisma();
		const bcrypt = await loadBcrypt();
		const user = await prisma.user.findUnique({
			where: { username },
		});

		if (!user) {
			// Dummy compare equalizes timing — without it an attacker can enumerate
			// valid usernames because bcrypt.compare is ~100ms and early-return is ~1ms.
			await bcrypt.compare(password, TIMING_DUMMY_HASH);
			return null;
		}

		const isValid = await bcrypt.compare(password, user.password);
		if (!isValid) {
			return null;
		}

		return { id: user.id, name: user.username };
	} catch {
		return null;
	}
}
