"use client";

import { useEffect } from "react";
import { signOut } from "next-auth/react";

export function SessionWatcher({ sessionError }: { sessionError?: string }) {
  useEffect(() => {
    if (sessionError === "RefreshAccessTokenError") {
      signOut({ callbackUrl: "/login?error=SessionExpired" });
    }
  }, [sessionError]);

  return null;
}
