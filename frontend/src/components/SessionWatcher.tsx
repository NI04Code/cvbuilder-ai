"use client";

import { useEffect } from "react";
import { signOut } from "next-auth/react";
import { usePathname } from "next/navigation";

export function SessionWatcher({ sessionError }: { sessionError?: string }) {
  const pathname = usePathname();

  useEffect(() => {
    if (sessionError === "RefreshAccessTokenError" || sessionError === "BackendSyncError") {
      const isPublicRoute = pathname.startsWith("/ats-checker");
      if (isPublicRoute) {
        signOut({ redirect: false });
      } else {
        signOut({ callbackUrl: "/login?error=SessionExpired" });
      }
    }
  }, [sessionError, pathname]);

  return null;
}
