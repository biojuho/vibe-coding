import { auth } from "@/auth";
import { redirect } from "next/navigation";

export class AuthenticationError extends Error {
  constructor(message = "Authentication required.") {
    super(message);
    this.name = "AuthenticationError";
  }
}

export async function requireAuthenticatedSession(options = {}) {
  const { redirectToLogin = false } = options;
  const session = await auth();

  if (!session?.user?.id) {
    if (redirectToLogin) {
      redirect("/login");
    }
    throw new AuthenticationError();
  }

  return session;
}

export function isAuthenticationError(error) {
  return error instanceof AuthenticationError || error?.name === "AuthenticationError";
}
