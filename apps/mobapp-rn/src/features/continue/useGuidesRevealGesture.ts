import { useCallback, useMemo, useRef, useState } from 'react';
import { Animated } from 'react-native';
import {
  State,
  type PanGestureHandlerGestureEvent,
  type PanGestureHandlerStateChangeEvent,
} from 'react-native-gesture-handler';

/** Left-edge strip that starts an open drag (does not wrap the FlatList). */
export const EDGE_WIDTH = 28;
/** Vertical travel that fails the edge/close pan so list scroll wins. */
export const FAIL_OFFSET_Y = 48;
/** Distance snap point — release nearer this side settles there. */
const SNAP = 0.5;
/** Min progress (from closed) for a right-fling to open. */
const FLING_OPEN_MIN = 0.2;
/** Max progress (from open) for a left-fling to close. */
const FLING_CLOSE_MAX = 0.8;
/** |vx| threshold for fling settle (px/s). */
const FLING_VX = 800;

function clamp01(n: number) {
  return Math.max(0, Math.min(1, n));
}

type Options = {
  openWidth: number;
};

/**
 * ChatGPT-style Guides reveal on Continue.
 *
 * Single source of truth: `progress` ∈ [0, 1].
 * translateX = progress * openWidth (via interpolate).
 *
 * Open: dedicated full-height edge strip (~28px) — FlatList keeps vertical scroll.
 * Close: pan on the main layer when open.
 * isOpen updates eagerly on ☰ / peek, and on settle after drag.
 * Finger math never reads isOpen — only dragOrigin + translationX / openWidth.
 *
 * Note: useNativeDriver springs do not mirror to JS listeners; BEGAN always
 * syncs origin via stopAnimation(callback) before finger-follow applies.
 */
export function useGuidesRevealGesture({ openWidth }: Options) {
  const progress = useRef(new Animated.Value(0)).current;
  const openWidthRef = useRef(openWidth);
  openWidthRef.current = openWidth;

  const [isOpen, setIsOpen] = useState(false);
  /** progress at BEGAN (stopAnimation) — ACTIVE = origin + tx / openWidth. */
  const dragOriginRef = useRef(0);
  /** Last progress written during ACTIVE (for END settle). */
  const lastProgressRef = useRef(0);
  /** True after stopAnimation callback — avoids follow before origin sync. */
  const dragReadyRef = useRef(false);
  /** Latest translation while waiting for origin sync. */
  const pendingTxRef = useRef(0);

  const translateX = useMemo(
    () =>
      progress.interpolate({
        inputRange: [0, 1],
        outputRange: [0, openWidth],
      }),
    [progress, openWidth],
  );

  const animateProgress = useCallback(
    (to: 0 | 1) => {
      dragReadyRef.current = false;
      progress.stopAnimation();
      Animated.spring(progress, {
        toValue: to,
        useNativeDriver: true,
        bounciness: 0,
        speed: 18,
      }).start(({ finished }) => {
        if (finished) {
          lastProgressRef.current = to;
          setIsOpen(to === 1);
        }
      });
    },
    [progress],
  );

  const openDrawer = useCallback(() => {
    setIsOpen(true);
    animateProgress(1);
  }, [animateProgress]);

  const closeDrawer = useCallback(() => {
    setIsOpen(false);
    animateProgress(0);
  }, [animateProgress]);

  const applyFollow = useCallback(
    (translationX: number) => {
      const openW = openWidthRef.current;
      if (openW <= 0) return;
      const next = clamp01(dragOriginRef.current + translationX / openW);
      lastProgressRef.current = next;
      progress.setValue(next);
    },
    [progress],
  );

  const beginDrag = useCallback(() => {
    dragReadyRef.current = false;
    pendingTxRef.current = 0;
    progress.stopAnimation((value) => {
      const origin = clamp01(value);
      dragOriginRef.current = origin;
      lastProgressRef.current = origin;
      dragReadyRef.current = true;
      // Apply any ACTIVE samples that arrived before this callback.
      applyFollow(pendingTxRef.current);
    });
  }, [applyFollow, progress]);

  const followFinger = useCallback(
    (translationX: number) => {
      pendingTxRef.current = translationX;
      if (!dragReadyRef.current) return;
      applyFollow(translationX);
    },
    [applyFollow],
  );

  const settleOpenGesture = useCallback(
    (p: number, velocityX: number) => {
      if (p >= SNAP || (p >= FLING_OPEN_MIN && velocityX > FLING_VX)) {
        setIsOpen(true);
        animateProgress(1);
      } else {
        setIsOpen(false);
        animateProgress(0);
      }
    },
    [animateProgress],
  );

  const settleCloseGesture = useCallback(
    (p: number, velocityX: number) => {
      if (p < SNAP || (p <= FLING_CLOSE_MAX && velocityX < -FLING_VX)) {
        setIsOpen(false);
        animateProgress(0);
      } else {
        setIsOpen(true);
        animateProgress(1);
      }
    },
    [animateProgress],
  );

  const snapToDragOrigin = useCallback(() => {
    const to: 0 | 1 = dragOriginRef.current >= SNAP ? 1 : 0;
    setIsOpen(to === 1);
    animateProgress(to);
  }, [animateProgress]);

  // --- Edge open (closed only) ---

  const onEdgeGestureEvent = useCallback(
    (e: PanGestureHandlerGestureEvent) => {
      followFinger(e.nativeEvent.translationX);
    },
    [followFinger],
  );

  const onEdgeHandlerStateChange = useCallback(
    (e: PanGestureHandlerStateChangeEvent) => {
      const { state, velocityX } = e.nativeEvent;

      if (state === State.BEGAN) {
        beginDrag();
        return;
      }

      if (state === State.CANCELLED || state === State.FAILED) {
        dragReadyRef.current = false;
        snapToDragOrigin();
        return;
      }

      if (state !== State.END) return;

      dragReadyRef.current = false;
      settleOpenGesture(lastProgressRef.current, velocityX);
    },
    [beginDrag, settleOpenGesture, snapToDragOrigin],
  );

  // --- Main close (open only) ---

  const onCloseGestureEvent = useCallback(
    (e: PanGestureHandlerGestureEvent) => {
      followFinger(e.nativeEvent.translationX);
    },
    [followFinger],
  );

  const onCloseHandlerStateChange = useCallback(
    (e: PanGestureHandlerStateChangeEvent) => {
      const { state, velocityX } = e.nativeEvent;

      if (state === State.BEGAN) {
        beginDrag();
        return;
      }

      if (state === State.CANCELLED || state === State.FAILED) {
        dragReadyRef.current = false;
        snapToDragOrigin();
        return;
      }

      if (state !== State.END) return;

      dragReadyRef.current = false;
      settleCloseGesture(lastProgressRef.current, velocityX);
    },
    [beginDrag, settleCloseGesture, snapToDragOrigin],
  );

  return {
    progress,
    translateX,
    isOpen,
    openDrawer,
    closeDrawer,
    edgePanProps: {
      enabled: !isOpen,
      onGestureEvent: onEdgeGestureEvent,
      onHandlerStateChange: onEdgeHandlerStateChange,
      activeOffsetX: 10,
      failOffsetY: [-FAIL_OFFSET_Y, FAIL_OFFSET_Y] as [number, number],
      shouldCancelWhenOutside: false,
      cancelsTouchesInView: false,
    },
    closePanProps: {
      enabled: isOpen,
      onGestureEvent: onCloseGestureEvent,
      onHandlerStateChange: onCloseHandlerStateChange,
      activeOffsetX: [-12, 12] as [number, number],
      failOffsetY: [-FAIL_OFFSET_Y, FAIL_OFFSET_Y] as [number, number],
      shouldCancelWhenOutside: false,
      cancelsTouchesInView: false,
    },
  };
}
