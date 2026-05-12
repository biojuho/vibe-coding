import assert from "node:assert/strict";
import { test } from "node:test";

import { authorizeCredentials } from "./auth-credentials.mjs";

function makeDeps({ user, passwordMatches = true, failDb = false } = {}) {
  return {
    loadPrisma: async () => ({
      user: {
        findUnique: async ({ where }) => {
          if (failDb) {
            throw new Error("database unavailable");
          }
          assert.equal(where.username, "admin");
          return user ?? null;
        },
      },
    }),
    loadBcrypt: async () => ({
      compare: async (plain, hashed) => {
        assert.equal(plain, "secret");
        assert.equal(hashed, "hashed-secret");
        return passwordMatches;
      },
    }),
  };
}

test("authorizeCredentials returns a session-safe user for valid credentials", async () => {
  const result = await authorizeCredentials(
    { username: "admin", password: "secret" },
    makeDeps({
      user: { id: "user-1", username: "admin", password: "hashed-secret" },
    }),
  );

  assert.deepEqual(result, { id: "user-1", name: "admin" });
});

test("authorizeCredentials rejects missing credentials without loading dependencies", async () => {
  const result = await authorizeCredentials(
    { username: "", password: "" },
    {
      loadPrisma: async () => {
        throw new Error("should not load prisma");
      },
      loadBcrypt: async () => {
        throw new Error("should not load bcrypt");
      },
    },
  );

  assert.equal(result, null);
});

test("authorizeCredentials rejects unknown users and wrong passwords", async () => {
  assert.equal(
    await authorizeCredentials({ username: "admin", password: "secret" }, makeDeps()),
    null,
  );
  assert.equal(
    await authorizeCredentials(
      { username: "admin", password: "secret" },
      makeDeps({
        user: { id: "user-1", username: "admin", password: "hashed-secret" },
        passwordMatches: false,
      }),
    ),
    null,
  );
});

test("authorizeCredentials degrades database errors to invalid credentials", async () => {
  const result = await authorizeCredentials(
    { username: "admin", password: "secret" },
    makeDeps({ failDb: true }),
  );

  assert.equal(result, null);
});
