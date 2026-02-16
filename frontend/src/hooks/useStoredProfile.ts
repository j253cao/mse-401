import { useCallback } from "react";
import type { StoredProfile } from "@/types/api";

const STORAGE_KEY = "uw-guide-profile";

export function useStoredProfile() {
  const read = useCallback((): StoredProfile | null => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as StoredProfile;
      if (parsed.programCode && parsed.incomingLevel) return parsed;
      return null;
    } catch {
      return null;
    }
  }, []);

  const write = useCallback((profile: StoredProfile | null) => {
    try {
      if (profile) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  return { read, write };
}
