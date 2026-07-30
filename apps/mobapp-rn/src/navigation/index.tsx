import React, { useMemo } from 'react';
import {
  DarkTheme,
  DefaultTheme,
  NavigationContainer,
  type Theme,
} from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { InstantAnswerScreen } from '@/features/intent/InstantAnswerScreen';
import { HistoryScreen } from '@/features/projects/HistoryScreen';
import { ProjectsScreen } from '@/features/projects/ProjectsScreen';
import {
  placeholderScreen,
  projectPlaceholderScreen,
} from '@/navigation/placeholders';
import type { RootStackParamList } from '@/navigation/types';
import { useTheme } from '@/theme/ThemeContext';

const Stack = createNativeStackNavigator<RootStackParamList>();

const IntentScreen = placeholderScreen('intent.title');
const DraftStudioScreen = projectPlaceholderScreen('draft.title');
const AcceptScreen = projectPlaceholderScreen('accept.title');
const ProjectHomeScreen = projectPlaceholderScreen('home.today');
const PathScreen = projectPlaceholderScreen('path.title');

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
        initialRouteName="Projects"
        screenOptions={{
          headerShown: true,
          headerShadowVisible: false,
          headerTransparent: false,
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.primary,
          headerTitleStyle: { color: colors.text },
          contentStyle: { backgroundColor: colors.background },
          // Keep UIKit chrome in lockstep with app theme (iOS 26 glass back btn).
          headerBlurEffect:
            effectiveTheme === 'dark'
              ? 'systemMaterialDark'
              : 'systemMaterialLight',
        }}
      >
        <Stack.Screen
          name="Projects"
          component={ProjectsScreen}
          options={{
            headerShown: false,
            title: 'Projects',
          }}
        />
        <Stack.Screen name="Intent" component={IntentScreen} />
        <Stack.Screen name="InstantAnswer" component={InstantAnswerScreen} />
        <Stack.Screen name="DraftStudio" component={DraftStudioScreen} />
        <Stack.Screen name="Accept" component={AcceptScreen} />
        <Stack.Screen name="ProjectHome" component={ProjectHomeScreen} />
        <Stack.Screen name="Path" component={PathScreen} />
        <Stack.Screen name="History" component={HistoryScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
