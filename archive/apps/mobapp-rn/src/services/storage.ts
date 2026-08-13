/**
 * MMKV with in-memory fallback (Expo Go / missing native module).
 */

import type { StateStorage } from 'zustand/middleware';

type MmkvLike = {
  getString: (key: string) => string | undefined;
  set: (key: string, value: string) => void;
  delete: (key: string) => void;
};

type Kv = {
  get: (key: string) => string | undefined;
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

function createKv(id: string): Kv {
  const mmkv = createMmkv(id);
  if (mmkv) {
    return {
      get: (key) => mmkv.getString(key),
      set: (key, value) => {
        mmkv.set(key, value);
      },
      delete: (key) => {
        mmkv.delete(key);
      },
    };
  }
  const mem: Record<string, string> = {};
  return {
    get: (key) => mem[key],
    set: (key, value) => {
      mem[key] = value;
    },
    delete: (key) => {
      delete mem[key];
    },
  };
}

export function buildZustandStorage(id: string): StateStorage {
  const kv = createKv(id);
  return {
    getItem: (name) => kv.get(name) ?? null,
    setItem: (name, value) => {
      kv.set(name, value);
    },
    removeItem: (name) => {
      kv.delete(name);
    },
  };
}

const DEVICE_ID_KEY = 'device_id';
const deviceKv = createKv('facio-device');

export function getStoredDeviceId(): string | null {
  return deviceKv.get(DEVICE_ID_KEY) ?? null;
}

export function setStoredDeviceId(id: string): void {
  deviceKv.set(DEVICE_ID_KEY, id);
}
