import React from 'react';
import { HeaderBackButton } from '@react-navigation/elements';
import type { NavigationProp } from '@react-navigation/native';
import type { NativeStackHeaderBackProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '@/navigation/types';

/**
 * Terminal exit from Session (Done / Skip / Postpone / Archive).
 * `navigate('Continue')` can leave Session under Continue (or push a second
 * Continue), so the iOS edge-swipe pops back to Session instead of opening
 * the Guides drawer. Reset to a single Continue root.
 */
export function resetToContinue(
  navigation: NavigationProp<RootStackParamList>,
) {
  navigation.reset({
    index: 0,
    routes: [{ name: 'Continue' }],
  });
}

/**
 * JS-backed goBack with Continue fallback. Shared by Session nav chip and
 * HeaderBackButton — native UIKit back can stop receiving taps on iOS 26.
 */
export function goBackOrContinue(
  navigation: NavigationProp<RootStackParamList>,
  fallback: 'Continue' = 'Continue',
) {
  if (navigation.canGoBack()) {
    navigation.goBack();
    return;
  }
  navigation.navigate(fallback);
}

/**
 * JS-backed header back control. Replaces the native UIKit back button, which
 * can stop receiving taps on iOS 26 (liquid glass) while the swipe gesture
 * still works — especially after re-entering a screen from a headerless root.
 */
export function renderReliableHeaderBack(
  navigation: NavigationProp<RootStackParamList>,
  props: NativeStackHeaderBackProps,
  fallback: 'Continue' = 'Continue',
  opts?: { hideLabel?: boolean },
) {
  if (!props.canGoBack) return null;

  return (
    <HeaderBackButton
      {...props}
      label={opts?.hideLabel ? '' : props.label}
      onPress={() => goBackOrContinue(navigation, fallback)}
    />
  );
}
