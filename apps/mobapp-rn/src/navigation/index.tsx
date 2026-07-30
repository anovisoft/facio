import React, { useMemo } from 'react';
import {
  DarkTheme,
  DefaultTheme,
  NavigationContainer,
  type Theme,
} from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { AcceptScreen } from '@/features/accept/AcceptScreen';
import { DraftStudioScreen } from '@/features/draft/DraftStudioScreen';
import { ProjectHomeScreen } from '@/features/home/ProjectHomeScreen';
import { InstantAnswerScreen } from '@/features/intent/InstantAnswerScreen';
import { IntentScreen } from '@/features/intent/IntentScreen';
import { PathScreen } from '@/features/path/PathScreen';
import { HistoryScreen } from '@/features/projects/HistoryScreen';
import { ProjectsScreen } from '@/features/projects/ProjectsScreen';
import { renderReliableHeaderBack } from '@/navigation/reliableBack';
import type { RootStackParamList } from '@/navigation/types';
import { useTheme } from '@/theme/ThemeContext';

const Stack = createNativeStackNavigator<RootStackParamList>();

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
            renderReliableHeaderBack(navigation, props, 'Projects'),
        })}
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
