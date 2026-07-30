/**
 * MMKV with in-memory fallback (Expo Go / missing native module).
 */

import type { StateStorage } from 'zustand/middleware';

type MmkvLike = {
  getString: (key: string) => string | undefined;
  set: (key: string, value: string) => void;
  delete: (key: string) => void;
};

function createMmkv(id: string): MmkvLike | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { MMKV } = require('react-native-mmkv') as {
      MMKV: new (opts: { id: string }) => MmkvLike;
    };
    return new MMKV({ id });
  } catch {
    return null;
  }
}

function memoryStorage(): StateStorage {
  const mem: Record<string, string> = {};
  return {
    getItem: (name) => mem[name] ?? null,
    setItem: (name, value) => {
      mem[name] = value;
    },
    removeItem: (name) => {
      delete mem[name];
    },
  };
}

export function buildZustandStorage(id: string): StateStorage {
  const mmkv = createMmkv(id);
  if (!mmkv) return memoryStorage();
  return {
    getItem: (name) => mmkv.getString(name) ?? null,
    setItem: (name, value) => {
      mmkv.set(name, value);
    },
    removeItem: (name) => {
      mmkv.delete(name);
    },
  };
}

const DEVICE_STORE_ID = 'facio-device';
const DEVICE_ID_KEY = 'device_id';

let deviceMmkv: MmkvLike | null | undefined;
const deviceMem: Record<string, string> = {};

function deviceBackend(): {
  get: (key: string) => string | undefined;
  set: (key: string, value: string) => void;
} {
  if (deviceMmkv === undefined) {
    deviceMmkv = createMmkv(DEVICE_STORE_ID);
  }
  if (deviceMmkv) {
    return {
      get: (key) => deviceMmkv!.getString(key),
      set: (key, value) => deviceMmkv!.set(key, value),
    };
  }
  return {
    get: (key) => deviceMem[key],
    set: (key, value) => {
      deviceMem[key] = value;
    },
  };
}

export function getStoredDeviceId(): string | null {
  return deviceBackend().get(DEVICE_ID_KEY) ?? null;
}

export function setStoredDeviceId(id: string): void {
  deviceBackend().set(DEVICE_ID_KEY, id);
}
