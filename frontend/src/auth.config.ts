import type { NextAuthConfig } from "next-auth";

export const authConfig = {
  providers: [], // Configured in auth.ts
  pages: {
    signIn: "/login",
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isProtectedRoute = nextUrl.pathname.startsWith("/dashboard") || 
                               nextUrl.pathname.startsWith("/profile") ||
                               nextUrl.pathname.startsWith("/generate");
      
      if (isProtectedRoute) {
        if (isLoggedIn) return true;
        return false; // Redirect to /login
      } else if (isLoggedIn && (nextUrl.pathname === "/login" || nextUrl.pathname === "/register")) {
        // Redirect logged in users away from auth pages
        return Response.redirect(new URL("/dashboard", nextUrl));
      }
      return true;
    },
  },
} satisfies NextAuthConfig;
