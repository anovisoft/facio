import React, { useCallback } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { LidFeed } from '@/components/LidFeed';
import { useDesk } from '@/store/DeskContext';
import { colors, spacing, typography } from '@/theme';
import type { RootStackParamList } from '@/navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Lid'>;

export function LidScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();
  const desk = useDesk();

  const onOpenUse = useCallback(
    (widgetId: string) => {
      navigation.navigate('Use', { widgetId });
    },
    [navigation],
  );

  const onCueSurfaced = useCallback(
    (widgetId: string) => {
      desk.markCueSurfaced(widgetId, 'tile');
    },
    [desk],
  );

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: insets.bottom + spacing.xl }}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.brand}>Facio</Text>
        <LidFeed
          widgets={desk.widgets}
          cueFor={desk.cueFor}
          onOpenUse={onOpenUse}
          onToggleTick={desk.toggleTick}
          onCueSurfaced={onCueSurfaced}
        />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background,
  },
  brand: {
    ...typography.caption,
    color: colors.textMuted,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
});
