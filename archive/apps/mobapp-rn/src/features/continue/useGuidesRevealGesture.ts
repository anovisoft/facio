import { useCallback, useEffect, useMemo, useState } from 'react';
import { Gesture } from 'react-native-gesture-handler';
import {
  cancelAnimation,
  Extrapolation,
  interpolate,
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  type SharedValue,
} from 'react-native-reanimated';

/** Left-edge strip that starts an open drag (does not wrap the FlatList). */
export const EDGE_WIDTH = 28;
/** Vertical travel that fails the pan so list scroll wins. */
export const FAIL_OFFSET_Y = 24;
/** Must move this far horizontally before the drawer gesture activates. */
const ACTIVE_OFFSET_X = 18;
/** |vx| above this (px/s) commits open/close regardless of midpoint. */
const FLING_VX = 550;

const SPRING = {
  stiffness: 220,
  damping: 28,
  mass: 0.85,
  overshootClamping: true,
  restDisplacementThreshold: 0.4,
  restSpeedThreshold: 0.4,
} as const;

function clamp(n: number, min: number, max: number) {
  'worklet';
  return Math.max(min, Math.min(max, n));
}

function buildRevealPan(options: {
  enabled: boolean;
  /** Positive = open (right); negative = close (left). */
  activeOffsetX: number;
  translateX: SharedValue<number>;
  openWidthSV: SharedValue<number>;
  dragOrigin: SharedValue<number>;
  dragging: SharedValue<boolean>;
  setOpenState: (open: boolean) => void;
}) {
  const {
    enabled,
    activeOffsetX,
    translateX,
    openWidthSV,
    dragOrigin,
    dragging,
    setOpenState,
  } = options;

  return Gesture.Pan()
    .enabled(enabled)
    .activeOffsetX(activeOffsetX)
    .failOffsetY([-FAIL_OFFSET_Y, FAIL_OFFSET_Y])
    .shouldCancelWhenOutside(false)
    .cancelsTouchesInView(false)
    .onStart((e) => {
      'worklet';
      cancelAnimation(translateX);
      const current = clamp(translateX.value, 0, openWidthSV.value);
      // Absorb activation travel so the panel does not jump by ~activeOffset.
      dragOrigin.value = current - e.translationX;
      dragging.value = true;
      translateX.value = clamp(
        dragOrigin.value + e.translationX,
        0,
        openWidthSV.value,
      );
    })
    .onUpdate((e) => {
      'worklet';
      if (!dragging.value) return;
      translateX.value = clamp(
        dragOrigin.value + e.translationX,
        0,
        openWidthSV.value,
      );
    })
    .onEnd((e) => {
      'worklet';
      if (!dragging.value) return;
      const width = openWidthSV.value;
      const pos = translateX.value;
      if (width <= 0) {
        dragging.value = false;
        return;
      }
      const velocityX = e.velocityX;
      let open: boolean;
      if (velocityX > FLING_VX) open = true;
      else if (velocityX < -FLING_VX) open = false;
      else open = pos > width * 0.5;

      dragging.value = false;
      cancelAnimation(translateX);
      translateX.value = withSpring(
        open ? width : 0,
        { ...SPRING, velocity: velocityX },
        (finished) => {
          if (!finished) return;
          // Flip only after settle — mid-spring enabled toggles used to hang pans.
          runOnJS(setOpenState)(open);
        },
      );
    })
    .onFinalize((_, success) => {
      'worklet';
      if (success || !dragging.value) return;
      const width = openWidthSV.value;
      const open = translateX.value > width * 0.5;
      dragging.value = false;
      cancelAnimation(translateX);
      translateX.value = withSpring(
        open ? width : 0,
        { ...SPRING, velocity: 0 },
        (finished) => {
          if (!finished) return;
          runOnJS(setOpenState)(open);
        },
      );
    });
}

type Options = {
  openWidth: number;
};

/**
 * ChatGPT-style Guides reveal on Continue.
 *
 * Finger-follow on a Reanimated shared value; spring settle on release.
 * Micro-moves ignored via activeOffsetX. UI-thread position — no JS Animated
 * listener / useNativeDriver: false races.
 */
export function useGuidesRevealGesture({ openWidth }: Options) {
  const translateX = useSharedValue(0);
  const openWidthSV = useSharedValue(openWidth);
  const dragOrigin = useSharedValue(0);
  const dragging = useSharedValue(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    openWidthSV.value = openWidth;
    if (!isOpen || dragging.value) return;
    translateX.value = openWidth;
  }, [dragging, isOpen, openWidth, openWidthSV, translateX]);

  const setOpenState = useCallback((open: boolean) => {
    setIsOpen(open);
  }, []);

  /** JS-thread open/close (☰ / peek tap). withSpring from JS is supported. */
  const springTo = useCallback(
    (open: boolean, velocityX = 0) => {
      const width = openWidthSV.value;
      const toValue = open ? width : 0;
      dragging.value = false;
      cancelAnimation(translateX);
      translateX.value = withSpring(
        toValue,
        { ...SPRING, velocity: velocityX },
        (finished) => {
          if (!finished) return;
          runOnJS(setOpenState)(open);
        },
      );
    },
    [dragging, openWidthSV, setOpenState, translateX],
  );

  const openDrawer = useCallback(() => {
    springTo(true);
  }, [springTo]);

  const closeDrawer = useCallback(() => {
    springTo(false);
  }, [springTo]);

  const edgeGesture = useMemo(
    () =>
      buildRevealPan({
        enabled: !isOpen,
        activeOffsetX: ACTIVE_OFFSET_X,
        translateX,
        openWidthSV,
        dragOrigin,
        dragging,
        setOpenState,
      }),
    [dragOrigin, dragging, isOpen, openWidthSV, setOpenState, translateX],
  );

  const closeGesture = useMemo(
    () =>
      buildRevealPan({
        enabled: isOpen,
        activeOffsetX: -ACTIVE_OFFSET_X,
        translateX,
        openWidthSV,
        dragOrigin,
        dragging,
        setOpenState,
      }),
    [dragOrigin, dragging, isOpen, openWidthSV, setOpenState, translateX],
  );

  const mainLayerStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    shadowOpacity: interpolate(
      translateX.value,
      [0, Math.max(openWidthSV.value, 1)],
      [0, 0.22],
      Extrapolation.CLAMP,
    ),
  }));

  return {
    isOpen,
    openDrawer,
    closeDrawer,
    edgeGesture,
    closeGesture,
    mainLayerStyle,
  };
}
