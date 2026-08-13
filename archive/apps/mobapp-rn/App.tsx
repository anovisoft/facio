import React, { Component, type ReactNode, useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as SplashScreen from 'expo-splash-screen';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import '@/i18n';
import AppNavigator from '@/navigation';
import { trackAppOpened } from '@/services/beacons';
import { getDeviceId } from '@/services/deviceId';
import {
  captureException,
  initSentry,
  wrapRootComponent,
} from '@/services/sentry';
import { useSessionStore } from '@/store';
import { ThemeProvider, useTheme } from '@/theme/ThemeContext';
import { lightColors, spacing, typography } from '@/theme';

initSentry();

SplashScreen.preventAutoHideAsync().catch(() => undefined);

class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: string | null }
> {
  state = { error: null as string | null };

  static getDerivedStateFromError(error: unknown) {
    return { error: String(error) };
  }

  componentDidCatch(error: unknown) {
    captureException(error);
  }

  render() {
    if (this.state.error) {
      return (
        <View style={styles.errorRoot}>
          <Text style={styles.errorText}>{this.state.error}</Text>
        </View>
      );
    }
    return this.props.children;
  }
}

function ThemedStatusBar() {
  const { effectiveTheme } = useTheme();
  return <StatusBar style={effectiveTheme === 'dark' ? 'light' : 'dark'} />;
}

function AppShell() {
  return (
    <>
      <ThemedStatusBar />
      <AppNavigator />
    </>
  );
}

function App() {
  const [hydrated, setHydrated] = useState(() =>
    useSessionStore.persist.hasHydrated(),
  );
  const themeMode = useSessionStore((s) => s.themeMode);

  useEffect(() => {
    if (hydrated) return;
    const unsub = useSessionStore.persist.onFinishHydration(() => {
      setHydrated(true);
    });
    if (useSessionStore.persist.hasHydrated()) setHydrated(true);
    return unsub;
  }, [hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    getDeviceId();
    trackAppOpened(useSessionStore.getState().lastProjectId);
    SplashScreen.hideAsync().catch(() => undefined);
  }, [hydrated]);

  if (!hydrated) {
    return <View style={styles.boot} />;
  }

  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={styles.flex}>
        <SafeAreaProvider>
          <ThemeProvider themeMode={themeMode}>
            <AppShell />
          </ThemeProvider>
        </SafeAreaProvider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  boot: { flex: 1, backgroundColor: lightColors.background },
  errorRoot: {
    flex: 1,
    backgroundColor: lightColors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  errorText: {
    ...typography.body,
    color: lightColors.error,
    textAlign: 'center',
  },
});

export default wrapRootComponent(App);
