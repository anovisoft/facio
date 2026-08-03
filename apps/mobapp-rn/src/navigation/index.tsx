import React, { useMemo } from 'react';
import {
  DarkTheme,
  DefaultTheme,
  NavigationContainer,
  type Theme,
} from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { ContinueScreen } from '@/features/continue/ContinueScreen';
import { GuideScreen } from '@/features/guide/GuideScreen';
import { ProjectHomeScreen } from '@/features/home/ProjectHomeScreen';
import { InstantAnswerScreen } from '@/features/intent/InstantAnswerScreen';
import { IntentScreen } from '@/features/intent/IntentScreen';
import { HistoryScreen } from '@/features/projects/HistoryScreen';
import { SettingsScreen } from '@/features/settings/SettingsScreen';
import { renderReliableHeaderBack } from '@/navigation/reliableBack';
import type { RootStackParamList } from '@/navigation/types';
import { useTheme } from '@/theme/ThemeContext';

const Stack = createNativeStackNavigator<RootStackParamList>();

/**
 * Facio 0.1 IA shell (Slice A+C).
 * Root = Continue. Guide = unified trust surface (draft + active).
 * GuideExplore is a thin alias of the same GuideScreen (Create seed).
 * Session / Create / Archive remain ProjectHome / Intent / History.
 * Settings is thin (theme) — ChatGPT gear destination from Guides.
 */
export default function AppNavigator() {
  const { colors, effectiveTheme } = useTheme();

  const navTheme = useMemo<Theme>(
    () => ({
      ...(effectiveTheme === 'dark' ? DarkTheme : DefaultTheme),
      dark: effectiveTheme === 'dark',
      colors: {
        ...(effectiveTheme === 'dark' ? DarkTheme.colors : DefaultTheme.colors),
        background: colors.background,
        card: colors.background,
        text: colors.text,
        border: colors.border,
        primary: colors.primary,
        notification: colors.primary,
      },
    }),
    [colors, effectiveTheme],
  );

  return (
    <NavigationContainer theme={navTheme}>
      <Stack.Navigator
        initialRouteName="Continue"
        screenOptions={({ navigation }) => ({
          headerShown: true,
          headerShadowVisible: false,
          headerTransparent: false,
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.primary,
          headerTitleStyle: { color: colors.text },
          contentStyle: { backgroundColor: colors.background },
          // Opaque header — avoid headerBlurEffect with headerTransparent:false;
          // the blur overlay has been linked to dead back-button taps on iOS 26.
          headerLeft: (props) =>
            renderReliableHeaderBack(navigation, props, 'Continue'),
        })}
      >
        <Stack.Screen
          name="Continue"
          component={ContinueScreen}
          options={{
            headerShown: false,
            title: 'Continue',
          }}
        />
        <Stack.Screen name="Create" component={IntentScreen} />
        {/* InstantAnswer kept registered but off Create happy path (D5). */}
        <Stack.Screen name="InstantAnswer" component={InstantAnswerScreen} />
        <Stack.Screen name="GuideExplore" component={GuideScreen} />
        <Stack.Screen name="Session" component={ProjectHomeScreen} />
        <Stack.Screen name="Guide" component={GuideScreen} />
        <Stack.Screen name="Archive" component={HistoryScreen} />
        <Stack.Screen name="Settings" component={SettingsScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
