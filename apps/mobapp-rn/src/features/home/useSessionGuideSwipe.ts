import { useCallback, useMemo, useRef } from 'react';
import { State } from 'react-native-gesture-handler';
import type {
  PanGestureHandlerGestureEvent,
  PanGestureHandlerStateChangeEvent,
} from 'react-native-gesture-handler';

/** Upward travel (px) before we commit Session → Guide. */
const OPEN_TRANSLATION_Y = -72;
/** Upward velocity (px/s) shortcut. */
const OPEN_VELOCITY_Y = -900;
/**
 * Activate only after clear upward intent so ScrollView keeps
 * vertical list / plugin scrolling (Continue drawer lesson).
 */
const ACTIVE_OFFSET_Y: [number, number] = [-36, 9999];
/** Fail pan if finger drifts sideways first. */
const FAIL_OFFSET_X: [number, number] = [-28, 28];

type Options = {
  enabled?: boolean;
  onOpenGuide: () => void;
};

/**
 * Session → Guide swipe-up. Does not touch Guides Continuereveal.
 * Back from Guide = stack back (header / system). Swipe-down on Session
 * is left to ScrollView — not a custom dismiss.
 */
export function useSessionGuideSwipe({
  enabled = true,
  onOpenGuide,
}: Options) {
  const translationY = useRef(0);
  const velocityY = useRef(0);
  const openedRef = useRef(false);

  const onGestureEvent = useCallback((e: PanGestureHandlerGestureEvent) => {
    translationY.current = e.nativeEvent.translationY;
    velocityY.current = e.nativeEvent.velocityY;
  }, []);

  const onHandlerStateChange = useCallback(
    (e: PanGestureHandlerStateChangeEvent) => {
      const { state } = e.nativeEvent;
      if (state === State.BEGAN || state === State.ACTIVE) {
        openedRef.current = false;
        return;
      }
      if (state !== State.END && state !== State.CANCELLED) return;
      if (openedRef.current || !enabled) return;

      const ty = e.nativeEvent.translationY;
      const vy = e.nativeEvent.velocityY;
      const shouldOpen =
        ty <= OPEN_TRANSLATION_Y || vy <= OPEN_VELOCITY_Y;
      if (!shouldOpen) return;

      openedRef.current = true;
      onOpenGuide();
    },
    [enabled, onOpenGuide],
  );

  const panProps = useMemo(
    () => ({
      enabled,
      onGestureEvent,
      onHandlerStateChange,
      activeOffsetY: ACTIVE_OFFSET_Y,
      failOffsetX: FAIL_OFFSET_X,
    }),
    [enabled, onGestureEvent, onHandlerStateChange],
  );

  return { panProps };
}
