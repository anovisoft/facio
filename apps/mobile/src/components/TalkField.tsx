import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { TalkRequestError } from '@/services/talk';
import { useDesk } from '@/store/DeskContext';
import { colors, radii, spacing, typography } from '@/theme';

type TalkFieldProps = {
  widgetId: string;
  bottomInset: number;
};

export function TalkField({ widgetId, bottomInset }: TalkFieldProps) {
  const desk = useDesk();
  const [draft, setDraft] = useState('');
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    const utterance = draft.trim();
    if (!utterance || busy) return;
    setBusy(true);
    try {
      const line = await desk.talkAbout(widgetId, utterance);
      setConfirmation(line);
      setDraft('');
    } catch (caught) {
      const message = caught instanceof TalkRequestError ? caught.message : 'так не записывается';
      setConfirmation(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={[styles.wrap, { marginBottom: bottomInset + spacing.sm }]}>
      <View style={styles.row}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          onSubmitEditing={() => {
            void send();
          }}
          placeholder="сказать про это"
          placeholderTextColor={colors.textMuted}
          returnKeyType="send"
          editable={!busy}
          style={styles.input}
          accessibilityLabel="сказать про это"
        />
        <Pressable
          onPress={() => {
            void send();
          }}
          disabled={busy || !draft.trim()}
          style={({ pressed }) => [styles.send, pressed && styles.pressed]}
          accessibilityLabel="отправить"
        >
          {busy ? (
            <ActivityIndicator color={colors.white} size="small" />
          ) : (
            <Text style={styles.sendText}>→</Text>
          )}
        </Pressable>
      </View>
      {confirmation ? (
        <Text style={styles.confirm} numberOfLines={1}>
          {confirmation}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginTop: spacing.md,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.text,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  send: {
    width: 40,
    height: 40,
    borderRadius: radii.pill,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendText: {
    ...typography.subtitle,
    color: colors.white,
  },
  confirm: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    paddingHorizontal: spacing.xs,
  },
  pressed: {
    opacity: 0.7,
  },
});
