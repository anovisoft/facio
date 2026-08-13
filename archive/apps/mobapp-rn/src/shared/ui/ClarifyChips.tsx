import React from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type { ClarifySelection } from '@/api/types';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  options: string[];
  onSelect: (option: string) => void;
  /** Single-select current value. */
  selected?: string | null;
  /** Multi-select current values (when selection=multi). */
  selectedValues?: string[];
  /** single = radio (default); multi = toggle several chips. */
  selection?: ClarifySelection;
  disabled?: boolean;
  /** When true, shows a free-text field under the chips (single mode). */
  allowCustom?: boolean;
  customPlaceholder?: string;
};

export function ClarifyChips({
  options,
  onSelect,
  selected,
  selectedValues,
  selection = 'single',
  disabled,
  allowCustom = false,
  customPlaceholder,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const isMulti = selection === 'multi';
  const value = selected ?? '';
  const multiSelected = selectedValues ?? [];
  const isCustom =
    !isMulti && value.length > 0 && !options.includes(value);

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        {options.map((option) => {
          const isSelected = isMulti
            ? multiSelected.includes(option)
            : selected === option;
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

      {allowCustom && !isMulti ? (
        <TextInput
          value={value}
          onChangeText={onSelect}
          editable={!disabled}
          textAlignVertical="center"
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
  // No typography.body.lineHeight — same iOS TextInput alignment fix as #11.
  input: {
    fontSize: typography.body.fontSize,
    fontWeight: typography.body.fontWeight,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
    minHeight: 44,
  },
});
