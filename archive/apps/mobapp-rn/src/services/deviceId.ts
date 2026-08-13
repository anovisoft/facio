import * as Crypto from 'expo-crypto';

import { getStoredDeviceId, setStoredDeviceId } from '@/services/storage';

let cached: string | null = null;

/** Stable per-install id → `X-Device-Id` for client-service auth. */
export function getDeviceId(): string {
  if (cached) return cached;
  const existing = getStoredDeviceId();
  if (existing) {
    cached = existing;
    return existing;
  }
  const id = Crypto.randomUUID();
  setStoredDeviceId(id);
  cached = id;
  return id;
}
