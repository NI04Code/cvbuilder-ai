const PROFILE_ONBOARDING_SKIPPED_PREFIX = "cvbuilder:profile_onboarding_skipped:";

export function isProfileOnboardingSkipped(userId?: string | null): boolean {
  if (typeof window === "undefined" || !userId) {
    return false;
  }
  try {
    return window.localStorage.getItem(`${PROFILE_ONBOARDING_SKIPPED_PREFIX}${userId}`) === "true";
  } catch {
    return false;
  }
}

export function markProfileOnboardingSkipped(userId?: string | null): void {
  if (typeof window === "undefined" || !userId) {
    return;
  }
  try {
    window.localStorage.setItem(`${PROFILE_ONBOARDING_SKIPPED_PREFIX}${userId}`, "true");
  } catch {
    // Ignore storage errors (e.g., private browsing quota)
  }
}

export function clearProfileOnboardingSkipped(userId?: string | null): void {
  if (typeof window === "undefined" || !userId) {
    return;
  }
  try {
    window.localStorage.removeItem(`${PROFILE_ONBOARDING_SKIPPED_PREFIX}${userId}`);
  } catch {
    // Ignore storage errors
  }
}
