import NextAuth from "next-auth";
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
  providers: [Google, GitHub],
  callbacks: {
    ...authConfig.callbacks,
    async jwt({ token, user, account, profile }) {
      // Initial sign in
      if (account && user) {
        try {
          // Sync with backend API
          const response = await apiClient.post("/auth/verify", {
            email: user.email,
            name: user.name,
            provider: account.provider,
            provider_account_id: account.providerAccountId,
            avatar_url: user.image,
            access_token: account.access_token,
          });

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
      
      // Return previous token if the access token has not expired yet
      if (!token.accessTokenExpires || !token.backendRefreshToken || Date.now() < (token.accessTokenExpires as number)) {
        return token;
      }

      // Access token has expired, try to update it
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
