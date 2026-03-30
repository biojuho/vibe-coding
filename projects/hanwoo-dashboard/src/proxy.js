import { NextResponse } from "next/server";

// Next.js 16: middleware.js → proxy.js (renamed from middleware)
// Ref: https://nextjs.org/docs/messages/middleware-to-proxy
export function proxy(request) {
  // Auth.js v5: session cookie check (lightweight proxy)
  // Auth.js v5 uses 'authjs.session-token' as cookie name
  const sessionToken =
    request.cookies.get("authjs.session-token")?.value ||
    request.cookies.get("__Secure-authjs.session-token")?.value;

  if (!sessionToken) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
