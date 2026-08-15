import React, { useCallback, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { LidFeed } from '@/components/LidFeed';
import { WhenModal } from '@/components/WhenModal';
import { clockPartsFromWindow } from '@/domain/reminder';
import { useDesk } from '@/store/DeskContext';
import { colors, spacing, typography } from '@/theme';
import type { RootStackParamList } from '@/navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Lid'>;

export function LidScreen({ navigation }: Props) {
  const insets = useSafeAreaInsets();
  const desk = useDesk();
  const [windowWidgetId, setWindowWidgetId] = useState<string | null>(null);

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

  const windowWidget = desk.widgets.find((item) => item.id === windowWidgetId);
  const windowSubject = desk.subjects.find((item) => item.id === windowWidget?.subject_id);
  const windowClock = useMemo(
    () => clockPartsFromWindow(windowSubject?.window, windowWidget?.payload.fire_at),
    [windowSubject?.window, windowWidget?.payload.fire_at],
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
          onOpenWindow={setWindowWidgetId}
        />
      </ScrollView>
      <WhenModal
        visible={windowWidgetId !== null}
        initialHours={windowClock.hours}
        initialMinutes={windowClock.minutes}
        onClose={() => setWindowWidgetId(null)}
        onSave={(hours, minutes) => {
          if (!windowWidgetId) return;
          void desk.setReminderWindow(windowWidgetId, hours, minutes);
          setWindowWidgetId(null);
        }}
        onDogfood={() => {
          if (windowWidgetId) void desk.fireDogfoodReminder(windowWidgetId);
        }}
      />
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
