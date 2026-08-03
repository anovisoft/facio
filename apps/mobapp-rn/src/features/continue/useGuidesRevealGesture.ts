import { useCallback, useEffect, useRef, useState } from 'react';
import { Animated } from 'react-native';
import {
  State,
  type PanGestureHandlerGestureEvent,
  type PanGestureHandlerStateChangeEvent,
} from 'react-native-gesture-handler';

/** Left-edge strip that starts an open drag (does not wrap the FlatList). */
export const EDGE_WIDTH = 28;
/** Vertical travel that fails the pan so list scroll wins. */
export const FAIL_OFFSET_Y = 24;
/** Must move this far horizontally before the drawer gesture activates. */
const ACTIVE_OFFSET_X = 18;
/** |vx| above this (px/s) commits open/close regardless of midpoint. */
const FLING_VX = 550;
/** Spring — iOS-ish drawer settle without bounce. */
const SPRING = {
  stiffness: 220,
  damping: 28,
  mass: 0.85,
  overshootClamping: true,
  restDisplacementThreshold: 0.4,
  restSpeedThreshold: 0.4,
  /**
   * JS driver on purpose: native-driver springs do not mirror to JS, so
   * stopAnimation/origin sync races and causes teleports / mid hangs.
   * One translateX is cheap enough at 60fps.
   */
  useNativeDriver: false as const,
};

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

type Options = {
  openWidth: number;
};

type SettleTarget = 'open' | 'closed';

/**
 * ChatGPT-style Guides reveal on Continue.
 *
 * Finger-follow while dragging; inertial spring to open/closed on release.
 * Micro-moves ignored via activeOffsetX. Single px position is the source of truth.
 */
export function useGuidesRevealGesture({ openWidth }: Options) {
  const translateX = useRef(new Animated.Value(0)).current;
  const openWidthRef = useRef(openWidth);
  const positionRef = useRef(0);
  const dragOriginRef = useRef(0);
  const draggingRef = useRef(false);
  const animatingRef = useRef(false);
  const [isOpen, setIsOpen] = useState(false);

  openWidthRef.current = openWidth;

  // JS-driver mirror — always know where the panel is (drag + spring).
  useEffect(() => {
    const id = translateX.addListener(({ value }) => {
      positionRef.current = value;
    });
    return () => {
      translateX.removeListener(id);
    };
  }, [translateX]);

  // If width changes while open (rotation), keep the panel fully revealed.
  useEffect(() => {
    if (!isOpen || draggingRef.current || animatingRef.current) return;
    positionRef.current = openWidth;
    translateX.setValue(openWidth);
  }, [isOpen, openWidth, translateX]);

  const animateTo = useCallback(
    (target: SettleTarget, velocityX = 0) => {
      const width = openWidthRef.current;
      const toValue = target === 'open' ? width : 0;
      animatingRef.current = true;
      draggingRef.current = false;
      translateX.stopAnimation();
      Animated.spring(translateX, {
        ...SPRING,
        toValue,
        // Keep fling momentum into the settle spring (px/s).
        velocity: velocityX,
      }).start(({ finished }) => {
        animatingRef.current = false;
        if (!finished) return;
        positionRef.current = toValue;
        setIsOpen(target === 'open');
      });
    },
    [translateX],
  );

  const openDrawer = useCallback(() => {
    animateTo('open');
  }, [animateTo]);

  const closeDrawer = useCallback(() => {
    animateTo('closed');
  }, [animateTo]);

  /**
   * Start finger-follow at ACTIVE (after activeOffset), not BEGAN.
   * Origin absorbs activation travel so the panel does not jump by ~18px.
   */
  const beginDrag = useCallback(
    (translationX: number) => {
      if (draggingRef.current) return;
      draggingRef.current = true;
      animatingRef.current = false;
      translateX.stopAnimation((value) => {
        const current = clamp(value, 0, openWidthRef.current);
        positionRef.current = current;
        dragOriginRef.current = current - translationX;
      });
    },
    [translateX],
  );

  const followFinger = useCallback(
    (translationX: number) => {
      if (!draggingRef.current) return;
      const next = clamp(
        dragOriginRef.current + translationX,
        0,
        openWidthRef.current,
      );
      positionRef.current = next;
      translateX.setValue(next);
    },
    [translateX],
  );

  const settle = useCallback(
    (velocityX: number) => {
      const width = openWidthRef.current;
      const pos = positionRef.current;
      if (width <= 0) {
        draggingRef.current = false;
        return;
      }

      let target: SettleTarget;
      if (velocityX > FLING_VX) {
        target = 'open';
      } else if (velocityX < -FLING_VX) {
        target = 'closed';
      } else {
        target = pos > width * 0.5 ? 'open' : 'closed';
      }

      // isOpen flips only in animateTo's finished callback — never mid-spring,
      // otherwise PanGestureHandler enabled toggles and the settle can hang.
      animateTo(target, velocityX);
    },
    [animateTo],
  );

  const cancelDrag = useCallback(() => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    const width = openWidthRef.current;
    const target: SettleTarget =
      positionRef.current > width * 0.5 ? 'open' : 'closed';
    animateTo(target, 0);
  }, [animateTo]);

  const onGestureEvent = useCallback(
    (e: PanGestureHandlerGestureEvent) => {
      followFinger(e.nativeEvent.translationX);
    },
    [followFinger],
  );

  const onHandlerStateChange = useCallback(
    (e: PanGestureHandlerStateChangeEvent) => {
      const { state, velocityX, translationX } = e.nativeEvent;

      // ACTIVE = passed activeOffset — real drag start (not BEGAN / micro-touch).
      if (state === State.ACTIVE) {
        beginDrag(translationX);
        followFinger(translationX);
        return;
      }

      if (state === State.CANCELLED || state === State.FAILED) {
        cancelDrag();
        return;
      }

      if (state === State.END) {
        if (!draggingRef.current) return;
        settle(velocityX);
      }
    },
    [beginDrag, cancelDrag, followFinger, settle],
  );

  return {
    translateX,
    isOpen,
    openDrawer,
    closeDrawer,
    edgePanProps: {
      enabled: !isOpen,
      onGestureEvent,
      onHandlerStateChange,
      activeOffsetX: ACTIVE_OFFSET_X,
      failOffsetY: [-FAIL_OFFSET_Y, FAIL_OFFSET_Y] as [number, number],
      shouldCancelWhenOutside: false,
      cancelsTouchesInView: false,
    },
    closePanProps: {
      enabled: isOpen,
      onGestureEvent,
      onHandlerStateChange,
      // Only a clear left drag starts close; right / micro-moves ignored.
      activeOffsetX: -ACTIVE_OFFSET_X,
      failOffsetY: [-FAIL_OFFSET_Y, FAIL_OFFSET_Y] as [number, number],
      shouldCancelWhenOutside: false,
      cancelsTouchesInView: false,
    },
  };
}
