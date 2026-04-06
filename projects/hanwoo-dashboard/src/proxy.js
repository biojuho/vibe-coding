export { auth as proxy } from "@/auth";

export const config = {
  matcher: [
    "/((?!login|privacy|terms|api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
};
