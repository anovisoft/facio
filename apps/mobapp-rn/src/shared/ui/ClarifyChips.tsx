import React from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useTranslation } from 'react-i18next';

import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  options: string[];
  onSelect: (option: string) => void;
  selected?: string | null;
  disabled?: boolean;
  /** When true, shows a free-text field under the chips. */
  allowCustom?: boolean;
  customPlaceholder?: string;
};

export function ClarifyChips({
  options,
  onSelect,
  selected,
  disabled,
  allowCustom = false,
  customPlaceholder,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const value = selected ?? '';
  const isCustom = value.length > 0 && !options.includes(value);

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        {options.map((option) => {
          const isSelected = selected === option;
          return (
            <Pressable
              key={option}
              disabled={disabled}
              onPress={() => onSelect(option)}
              style={({ pressed }) => [
                styles.chip,
                {
                  backgroundColor: isSelected
                    ? colors.primary
                    : colors.surface,
                  borderColor: isSelected ? colors.primary : colors.border,
                  opacity: disabled ? 0.5 : pressed ? 0.85 : 1,
                },
              ]}
            >
              <Text
                style={[
                  styles.label,
                  {
                    color: isSelected ? colors.white : colors.primary,
                  },
                ]}
              >
                {option}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {allowCustom ? (
        <TextInput
          value={value}
          onChangeText={onSelect}
          editable={!disabled}
          placeholder={
            customPlaceholder ?? t('draft.freeTextPlaceholder')
          }
          placeholderTextColor={colors.textMuted}
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: isCustom ? colors.primary : colors.border,
              opacity: disabled ? 0.5 : 1,
            },
          ]}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    borderWidth: 1,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  label: {
    ...typography.caption,
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minHeight: 44,
  },
});
