/**
 * Optional Sentry. Without EXPO_PUBLIC_SENTRY_DSN — no-op.
 */

import type { ComponentType } from 'react';

import * as Sentry from '@sentry/react-native';

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN?.trim() || undefined;

export function initSentry(): void {
  Sentry.init({
    dsn,
    enabled: Boolean(dsn),
    tracesSampleRate: dsn ? 0.2 : 0,
    enableAutoSessionTracking: Boolean(dsn),
  });
}

export function wrapRootComponent(
  Component: ComponentType,
): ComponentType {
  if (!dsn) return Component;
  return Sentry.wrap(Component);
}

export function captureException(error: unknown): void {
  if (!dsn) return;
  Sentry.captureException(error);
}
