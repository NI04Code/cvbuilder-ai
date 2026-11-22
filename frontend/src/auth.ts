import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import GitHub from "next-auth/providers/github";
import { authConfig } from "./auth.config";
import { apiClient } from "@/lib/api";

async function refreshAccessToken(token: any) {
  try {
    const response = await apiClient.post("/auth/refresh", {
      refresh_token: token.backendRefreshToken,
    });

    return {
      ...token,
      backendAccessToken: response.data.access_token,
      backendRefreshToken: response.data.refresh_token,
      accessTokenExpires: Date.now() + response.data.expires_in * 1000,
    };
  } catch (error) {
    console.error("Error refreshing access token", error);
    return {
      ...token,
      error: "RefreshAccessTokenError",
    };
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Google,
    GitHub,
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (
          typeof credentials?.email !== "string" ||
          typeof credentials?.password !== "string"
        ) {
          return null;
        }

        try {
          const response = await apiClient.post("/auth/login", {
            email: credentials.email,
            password: credentials.password,
          });
          const { user, tokens } = response.data;
          return {
            id: user.id,
            email: user.email,
            name: user.name,
            image: user.avatar_url ?? null,
            backendAccessToken: tokens.access_token,
            backendRefreshToken: tokens.refresh_token,
            accessTokenExpires: Date.now() + tokens.expires_in * 1000,
            hasProfile: user.has_profile,
          } as any;
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    ...authConfig.callbacks,
    async jwt({ token, user, account, trigger, session }) {
      if (trigger === "update" && session?.hasProfile !== undefined) {
        token.hasProfile = session.hasProfile;
      }
      // Initial sign in
      if (account && user) {
        if (account.provider === "credentials") {
          const manualUser = user as any;
          token.backendAccessToken = manualUser.backendAccessToken;
          token.backendRefreshToken = manualUser.backendRefreshToken;
          token.accessTokenExpires = manualUser.accessTokenExpires;
          token.userId = manualUser.id;
          token.hasProfile = manualUser.hasProfile;
          return token;
        }

        try {
          // Sync with backend API
          const internalSecret = process.env.INTERNAL_AUTH_SECRET;
          const response = await apiClient.post(
            "/auth/verify",
            {
              email: user.email,
              name: user.name,
              provider: account.provider,
              provider_account_id: account.providerAccountId,
              avatar_url: user.image,
              access_token: account.access_token,
            },
            {
              headers: internalSecret
                ? { "X-Internal-Auth-Secret": internalSecret }
                : undefined,
            }
          );

          // Store backend JWT tokens in NextAuth session token
          token.backendAccessToken = response.data.tokens.access_token;
          token.backendRefreshToken = response.data.tokens.refresh_token;
          token.accessTokenExpires = Date.now() + response.data.tokens.expires_in * 1000;
          token.userId = response.data.user.id;
          token.hasProfile = response.data.user.has_profile;
          
          return token;
        } catch (error) {
          console.error("Error syncing user with backend:", error);
          return { ...token, error: "BackendSyncError" };
        }
      }
      
      // Refresh proactively when within 5 minutes of expiry (or on explicit forceRefresh)
      const REFRESH_BUFFER_MS = 5 * 60 * 1000;
      if (
        !(trigger === "update" && (session as any)?.forceRefresh) &&
        (!token.accessTokenExpires ||
          !token.backendRefreshToken ||
          Date.now() < (token.accessTokenExpires as number) - REFRESH_BUFFER_MS)
      ) {
        return token;
      }

      // Access token is expired or nearing expiry, refresh via backend
      return await refreshAccessToken(token);
    },
    async session({ session, token }) {
      if (token) {
        session.user.id = token.userId as string;
        // Extend session type with our backend specific fields if needed
        (session as any).backendAccessToken = token.backendAccessToken;
        (session as any).hasProfile = token.hasProfile;
        (session as any).error = token.error;
      }
      return session;
    },
  },
});
