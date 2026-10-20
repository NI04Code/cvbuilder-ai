import NextAuth from "next-auth";
import { authConfig } from "@/auth.config";

const { auth } = NextAuth(authConfig);
export default auth;

export const config = {
  // Specify routes to protect using the Next.js matcher
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
