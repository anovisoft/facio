import React from 'react';
import { HeaderBackButton } from '@react-navigation/elements';
import type { NavigationProp } from '@react-navigation/native';
import type { NativeStackHeaderBackProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '@/navigation/types';

/**
 * JS-backed header back control. Replaces the native UIKit back button, which
 * can stop receiving taps on iOS 26 (liquid glass) while the swipe gesture
 * still works — especially after re-entering a screen from a headerless root.
 */
export function renderReliableHeaderBack(
  navigation: NavigationProp<RootStackParamList>,
  props: NativeStackHeaderBackProps,
  fallback: 'Projects' = 'Projects',
) {
  if (!props.canGoBack) return null;

  return (
    <HeaderBackButton
      {...props}
      onPress={() => {
        if (navigation.canGoBack()) {
          navigation.goBack();
          return;
        }
        navigation.navigate(fallback);
      }}
    />
  );
}
