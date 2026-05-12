export async function authorizeCredentials(credentials, deps = {}) {
  const username = typeof credentials?.username === "string" ? credentials.username : "";
  const password = typeof credentials?.password === "string" ? credentials.password : "";

  if (!username || !password) {
    return null;
  }

  const loadPrisma = deps.loadPrisma ?? (async () => (await import("@/lib/db")).default);
  const loadBcrypt = deps.loadBcrypt ?? (async () => (await import("bcrypt")).default);

  try {
    const prisma = await loadPrisma();
    const bcrypt = await loadBcrypt();
    const user = await prisma.user.findUnique({
      where: { username },
    });

    if (!user) {
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
