import * as Crypto from 'expo-crypto';
import type * as Notifications from 'expo-notifications';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { formatClock, formatLocalDate, formatLocalDateTime, nextReminderFireAt } from '@/domain/reminder';
import { doTimeCueFor } from '@/domain/seed';
import { COMPACT_TILE, type Cue, type DeskSnapshot, type Instance, type Subject, type Widget, type Window } from '@/domain/types';
import {
  PERMISSION_META_KEY,
  cancelWidgetNotifications,
  ensureNotificationPermission,
  fireAtFromPayload,
  reminderDataOf,
  scheduleCombatReminder,
  scheduleDogfoodReminder,
} from '@/services/reminders';
import { getDb } from './database';
import {
  appendEvent,
  ensureBike,
  ensureBikeFoundingSilence,
  getMeta,
  loadSnapshot,
  MORNING_CLOSED_META_KEY,
  restoreTodayDone,
  revertLookOnlyStarts,
  saveWidget,
  saveCue,
  saveInstance,
  saveSubject,
  seedIfEmpty,
  restoreBikeDrift,
  setMeta,
} from './repository';

type DeskContextValue = DeskSnapshot & {
  ready: boolean;
  error: string | null;
  cueFor: (subjectId: string) => Cue | undefined;
  startInstance: (widgetId: string) => void;
  markCueSurfaced: (widgetId: string, place: 'tile' | 'use') => void;
  tickCounter: (widgetId: string, delta: number) => void;
  completeCounter: (widgetId: string) => void;
  toggleTick: (widgetId: string) => void;
  completeReminder: (widgetId: string) => void;
  setReminderWindow: (widgetId: string, hours: number, minutes: number) => Promise<void>;
  editCueText: (cueId: string, text: string) => void;
  editTarget: (widgetId: string, goal: number) => void;
  syncReminders: () => Promise<void>;
  fireDogfoodReminder: (widgetId: string) => Promise<void>;
  noteReminderFired: (notification: Notifications.Notification) => void;
  noteReminderOpened: (notification: Notifications.Notification) => void;
  morningClosedOn: string | null;
  answerDrift: (subjectId: string, action: 'today' | 'weekly' | 'retire') => void;
  answerDelta: (widgetId: string, action: 'yes' | 'leave' | 'later') => void;
  restoreBikeDrift: (days: 8 | 21) => void;
};

const DeskContext = createContext<DeskContextValue | null>(null);

const empty: DeskSnapshot = {
  subjects: [],
  cues: [],
  instances: [],
  widgets: [],
};

function replaceById<T extends { id: string }>(list: T[], next: T): T[] {
  return list.map((item) => (item.id === next.id ? next : item));
}

export function DeskProvider({ children }: { children: React.ReactNode }) {
  const [snapshot, setSnapshot] = useState<DeskSnapshot>(empty);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [morningClosedOn, setMorningClosedOn] = useState<string | null>(null);
  const surfacedKeys = useRef(new Set<string>());
  const reminderLogKeys = useRef(new Set<string>());

  useEffect(() => {
    try {
      const database = getDb();
      seedIfEmpty(database);
      ensureBike(database);
      ensureBikeFoundingSilence(database);
      restoreTodayDone(database);
      setMorningClosedOn(getMeta(database, MORNING_CLOSED_META_KEY));
      setSnapshot(revertLookOnlyStarts(database));
      setReady(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }, []);

  const persist = useCallback((next: DeskSnapshot) => {
    setSnapshot(next);
  }, []);

  const cueFor = useCallback(
    (subjectId: string) => doTimeCueFor(snapshot.cues, subjectId),
    [snapshot.cues],
  );

  /** Real start only — first +/- or analog. Use must not call this on open. */
  const startInstance = useCallback(
    (widgetId: string) => {
      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const instance = snapshot.instances.find((item) => item.id === widget?.instance_id);
      if (!widget || !instance || instance.status !== 'prepared') return;

      const nextInstance: Instance = { ...instance, status: 'in_progress' };
      const nextWidget: Widget = { ...widget, status: 'running' };
      saveInstance(database, nextInstance);
      saveWidget(database, nextWidget);
      appendEvent(database, 'instance_started', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: instance.id,
      });
      persist({
        ...snapshot,
        instances: replaceById(snapshot.instances, nextInstance),
        widgets: replaceById(snapshot.widgets, nextWidget),
      });
    },
    [persist, snapshot],
  );

  const markCueSurfaced = useCallback(
    (widgetId: string, place: 'tile' | 'use') => {
      const key = `${widgetId}:${place}`;
      if (surfacedKeys.current.has(key)) return;
      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const cue = widget ? doTimeCueFor(snapshot.cues, widget.subject_id) : undefined;
      if (!widget || !cue) return;
      surfacedKeys.current.add(key);

      const nextCue: Cue = {
        ...cue,
        hits: { ...cue.hits, surfaced: cue.hits.surfaced + 1 },
      };
      saveCue(database, nextCue);
      appendEvent(database, 'cue_surfaced', {
        subject_id: cue.subject_id,
        widget_id: widget.id,
        instance_id: widget.instance_id,
        cue_id: cue.id,
        payload: { text: cue.text, place },
      });
      persist({ ...snapshot, cues: replaceById(snapshot.cues, nextCue) });
    },
    [persist, snapshot],
  );

  const applyCueIfAny = useCallback((widget: Widget, cues: Cue[]): Cue[] => {
    const cue = doTimeCueFor(cues, widget.subject_id);
    if (!cue) return cues;
    const nextCue: Cue = {
      ...cue,
      hits: { ...cue.hits, applied: cue.hits.applied + 1 },
    };
    const database = getDb();
    saveCue(database, nextCue);
    appendEvent(database, 'cue_applied', {
      subject_id: cue.subject_id,
      widget_id: widget.id,
      instance_id: widget.instance_id,
      cue_id: cue.id,
    });
    return replaceById(cues, nextCue);
  }, []);

  const finishInstance = useCallback(
    (widget: Widget, instance: Instance, nextWidget: Widget, cues: Cue[]) => {
      const database = getDb();
      const when = formatLocalDateTime(new Date());
      const completed: Instance = { ...instance, status: 'completed', when };
      const standing: Widget = {
        ...nextWidget,
        status: 'done',
        section: 'today',
        when,
      };
      saveInstance(database, completed);
      saveWidget(database, standing);
      appendEvent(database, 'instance_completed', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: instance.id,
      });
      return {
        instances: replaceById(snapshot.instances, completed),
        widgets: replaceById(snapshot.widgets, standing),
        cues: applyCueIfAny(widget, cues),
      };
    },
    [applyCueIfAny, snapshot.instances],
  );

  const tickCounter = useCallback(
    (widgetId: string, delta: number) => {
      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const instance = snapshot.instances.find((item) => item.id === widget?.instance_id);
      if (!widget || widget.type !== 'counter' || !instance || instance.status === 'completed') {
        return;
      }

      let workingInstance = instance;
      let instances = snapshot.instances;
      let nextWidget: Widget = widget;
      if (instance.status === 'prepared') {
        workingInstance = { ...instance, status: 'in_progress' };
        saveInstance(database, workingInstance);
        appendEvent(database, 'instance_started', {
          subject_id: widget.subject_id,
          widget_id: widget.id,
          instance_id: instance.id,
        });
        instances = replaceById(snapshot.instances, workingInstance);
        nextWidget = { ...widget, status: 'running' };
      }

      const current = nextWidget.payload.count ?? 0;
      const target = nextWidget.payload.target ?? 0;
      const nextCount = Math.max(0, current + delta);
      nextWidget = {
        ...nextWidget,
        status: nextWidget.status === 'ready' ? 'running' : nextWidget.status,
        payload: { ...nextWidget.payload, count: nextCount },
      };
      saveWidget(database, nextWidget);
      appendEvent(database, 'counter_ticked', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: widget.instance_id,
        payload: { count: nextCount, delta },
      });

      const subject = snapshot.subjects.find((item) => item.id === widget.subject_id);
      let subjects = snapshot.subjects;
      if (subject?.target) {
        const nextSubject: Subject = {
          ...subject,
          target: { ...subject.target, current: nextCount },
        };
        saveSubject(database, nextSubject);
        subjects = replaceById(snapshot.subjects, nextSubject);
      }

      persist({
        ...snapshot,
        instances,
        widgets: replaceById(snapshot.widgets, nextWidget),
        subjects,
      });

      if (target > 0 && nextCount >= target) {
        const finished = finishInstance(widget, workingInstance, nextWidget, snapshot.cues);
        persist({ ...snapshot, subjects, ...finished });
      }
    },
    [finishInstance, persist, snapshot],
  );

  const completeCounter = useCallback(
    (widgetId: string) => {
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const instance = snapshot.instances.find((item) => item.id === widget?.instance_id);
      if (!widget || !instance || instance.status === 'completed') return;
      persist({
        ...snapshot,
        ...finishInstance(widget, instance, widget, snapshot.cues),
      });
    },
    [finishInstance, persist, snapshot],
  );

  const toggleTick = useCallback(
    (widgetId: string) => {
      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const instance = snapshot.instances.find((item) => item.id === widget?.instance_id);
      if (!widget || widget.type !== 'tick' || !instance || instance.status === 'completed') {
        return;
      }

      if (instance.status === 'prepared') {
        const started: Instance = { ...instance, status: 'in_progress' };
        saveInstance(database, started);
        appendEvent(database, 'instance_started', {
          subject_id: widget.subject_id,
          widget_id: widget.id,
          instance_id: instance.id,
        });
      }

      const nextWidget: Widget = {
        ...widget,
        payload: { ...widget.payload, done: true },
      };
      saveWidget(database, nextWidget);
      appendEvent(database, 'tick_toggled', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: widget.instance_id,
        payload: { done: true },
      });

      const standing = nextWidget;
      persist({
        ...snapshot,
        ...finishInstance(widget, { ...instance, status: 'in_progress' }, standing, snapshot.cues),
      });
    },
    [finishInstance, persist, snapshot],
  );

  const completeReminder = useCallback(
    (widgetId: string) => {
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const instance = snapshot.instances.find((item) => item.id === widget?.instance_id);
      if (!widget || widget.type !== 'reminder' || !instance || instance.status === 'completed') {
        return;
      }

      const database = getDb();
      let working: Instance = instance;
      if (instance.status === 'prepared') {
        working = { ...instance, status: 'in_progress' };
        saveInstance(database, working);
        appendEvent(database, 'instance_started', {
          subject_id: widget.subject_id,
          widget_id: widget.id,
          instance_id: instance.id,
        });
      }

      void cancelWidgetNotifications(widget.id);
      persist({
        ...snapshot,
        ...finishInstance(widget, working, widget, snapshot.cues),
      });
    },
    [finishInstance, persist, snapshot],
  );

  const setReminderWindow = useCallback(
    async (widgetId: string, hours: number, minutes: number) => {
      const database = getDb();
      const current = loadSnapshot(database);
      const widget = current.widgets.find((item) => item.id === widgetId);
      const subject = current.subjects.find((item) => item.id === widget?.subject_id);
      if (!widget || widget.type !== 'reminder' || !subject) return;

      const latestBy = formatClock(hours, minutes);
      const nextWindow: Window = {
        latest_by: latestBy,
        closes_at: subject.window?.closes_at ?? null,
      };
      const nextSubject: Subject = {
        ...subject,
        window: nextWindow,
      };
      saveSubject(database, nextSubject);

      const fireAt = nextReminderFireAt(nextWindow, new Date());
      const fireIso = formatLocalDateTime(fireAt);

      let instances = current.instances;
      const instance = current.instances.find((item) => item.id === widget.instance_id);
      if (instance && instance.status !== 'completed') {
        const nextInstance: Instance = { ...instance, when: fireIso };
        saveInstance(database, nextInstance);
        instances = replaceById(current.instances, nextInstance);
      }

      const asked = getMeta(database, PERMISSION_META_KEY) === '1';
      const allowed = await ensureNotificationPermission({ alreadyAsked: asked });
      if (!asked) setMeta(database, PERMISSION_META_KEY, '1');

      const nextWidget: Widget = {
        ...widget,
        when: fireIso,
        payload: { ...widget.payload, fire_at: fireIso },
      };
      if (allowed) {
        await cancelWidgetNotifications(widget.id, ['combat']);
        const notificationId = await scheduleCombatReminder(nextWidget, fireAt);
        nextWidget.payload = { ...nextWidget.payload, os_notification_id: notificationId };
      }

      saveWidget(database, nextWidget);
      appendEvent(database, 'reminder_scheduled', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: widget.instance_id,
        payload: {
          fire_at: fireIso,
          latest_by: latestBy,
          notification_id: nextWidget.payload.os_notification_id,
          kind: 'combat',
          source: 'window',
        },
      });
      persist({
        ...current,
        subjects: replaceById(current.subjects, nextSubject),
        instances,
        widgets: replaceById(current.widgets, nextWidget),
      });
    },
    [persist],
  );

  const editCueText = useCallback(
    (cueId: string, text: string) => {
      const database = getDb();
      const cue = snapshot.cues.find((item) => item.id === cueId);
      if (!cue || cue.text === text) return;
      const nextCue: Cue = { ...cue, text };
      saveCue(database, nextCue);
      appendEvent(database, 'cue_written', {
        subject_id: cue.subject_id,
        cue_id: cue.id,
        payload: { text, previous: cue.text },
      });
      persist({ ...snapshot, cues: replaceById(snapshot.cues, nextCue) });
    },
    [persist, snapshot],
  );

  const editTarget = useCallback(
    (widgetId: string, goal: number) => {
      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const subject = snapshot.subjects.find((item) => item.id === widget?.subject_id);
      if (!widget || !Number.isFinite(goal) || goal < 1) return;

      const nextWidget: Widget = {
        ...widget,
        payload: { ...widget.payload, target: goal },
      };
      saveWidget(database, nextWidget);

      let subjects = snapshot.subjects;
      if (subject) {
        const nextSubject: Subject = {
          ...subject,
          target: {
            current: subject.target?.current ?? widget.payload.count ?? 0,
            goal,
          },
        };
        saveSubject(database, nextSubject);
        subjects = replaceById(snapshot.subjects, nextSubject);
      }

      persist({
        ...snapshot,
        widgets: replaceById(snapshot.widgets, nextWidget),
        subjects,
      });
    },
    [persist, snapshot],
  );

  const syncReminders = useCallback(async () => {
    const database = getDb();
    const current = loadSnapshot(database);
    const widget = current.widgets.find((item) => item.type === 'reminder');
    const subject = current.subjects.find((item) => item.id === widget?.subject_id);
    if (!widget || !subject?.window) return;

    const asked = getMeta(database, PERMISSION_META_KEY) === '1';
    const allowed = await ensureNotificationPermission({ alreadyAsked: asked });
    if (!asked) setMeta(database, PERMISSION_META_KEY, '1');
    if (!allowed) return;

    let fireAt = fireAtFromPayload(widget.payload.fire_at);
    const now = new Date();
    if (!fireAt || fireAt.getTime() <= now.getTime()) {
      fireAt = nextReminderFireAt(subject.window, now);
    }
    const fireIso = formatLocalDateTime(fireAt);

    await cancelWidgetNotifications(widget.id, ['combat']);
    const nextWidget: Widget = {
      ...widget,
      when: fireIso,
      payload: { ...widget.payload, fire_at: fireIso },
    };
    const notificationId = await scheduleCombatReminder(nextWidget, fireAt);
    nextWidget.payload = { ...nextWidget.payload, os_notification_id: notificationId };
    saveWidget(database, nextWidget);
    appendEvent(database, 'reminder_scheduled', {
      subject_id: widget.subject_id,
      widget_id: widget.id,
      instance_id: widget.instance_id,
      payload: { fire_at: fireIso, notification_id: notificationId, kind: 'combat' },
    });
    persist({
      ...current,
      widgets: replaceById(current.widgets, nextWidget),
    });
  }, [persist]);

  const fireDogfoodReminder = useCallback(async (widgetId: string) => {
    const database = getDb();
    const current = loadSnapshot(database);
    const widget = current.widgets.find((item) => item.id === widgetId);
    if (!widget || widget.type !== 'reminder') return;

    const allowed = await ensureNotificationPermission({ force: true });
    if (!allowed) return;

    const subject = current.subjects.find((item) => item.id === widget.subject_id);
    if (subject?.window && !widget.payload.os_notification_id) {
      let fireAt = fireAtFromPayload(widget.payload.fire_at);
      const now = new Date();
      if (!fireAt || fireAt.getTime() <= now.getTime()) {
        fireAt = nextReminderFireAt(subject.window, now);
      }
      const fireIso = formatLocalDateTime(fireAt);
      const combatWidget: Widget = {
        ...widget,
        when: fireIso,
        payload: { ...widget.payload, fire_at: fireIso },
      };
      const combatId = await scheduleCombatReminder(combatWidget, fireAt);
      combatWidget.payload = { ...combatWidget.payload, os_notification_id: combatId };
      saveWidget(database, combatWidget);
      appendEvent(database, 'reminder_scheduled', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: widget.instance_id,
        payload: { fire_at: fireIso, notification_id: combatId, kind: 'combat' },
      });
      current.widgets = replaceById(current.widgets, combatWidget);
    }

    const live = current.widgets.find((item) => item.id === widgetId) ?? widget;
    await cancelWidgetNotifications(live.id, ['dogfood']);
    const notificationId = await scheduleDogfoodReminder(live);
    const nextWidget: Widget = {
      ...live,
      payload: { ...live.payload, dogfood_notification_id: notificationId },
    };
    saveWidget(database, nextWidget);
    appendEvent(database, 'reminder_scheduled', {
      subject_id: widget.subject_id,
      widget_id: widget.id,
      instance_id: widget.instance_id,
      payload: { notification_id: notificationId, kind: 'dogfood', seconds: 60 },
    });
    persist({
      ...current,
      widgets: replaceById(current.widgets, nextWidget),
    });
  }, [persist]);

  const noteReminderEvent = useCallback(
    (type: 'reminder_fired' | 'reminder_opened', notification: Notifications.Notification) => {
      const data = reminderDataOf(notification);
      if (!data) return;
      const key = `${type}:${notification.request.identifier}`;
      if (reminderLogKeys.current.has(key)) return;
      reminderLogKeys.current.add(key);

      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === data.widgetId);
      appendEvent(database, type, {
        subject_id: data.subjectId,
        widget_id: data.widgetId,
        instance_id: widget?.instance_id ?? null,
        payload: { kind: data.kind, notification_id: notification.request.identifier },
      });
    },
    [snapshot.widgets],
  );

  const noteReminderFired = useCallback(
    (notification: Notifications.Notification) => {
      noteReminderEvent('reminder_fired', notification);
    },
    [noteReminderEvent],
  );

  const noteReminderOpened = useCallback(
    (notification: Notifications.Notification) => {
      noteReminderEvent('reminder_opened', notification);
    },
    [noteReminderEvent],
  );

  const placeSubjectOnToday = useCallback(
    (current: DeskSnapshot, subject: Subject, now: Date): DeskSnapshot => {
      const hidden = new Set(['done', 'skipped', 'archived', 'snoozed']);
      const live = current.widgets.find(
        (item) =>
          item.subject_id === subject.id &&
          item.section === 'today' &&
          !hidden.has(item.status),
      );
      if (live) return current;

      const parked = current.widgets.find(
        (item) =>
          item.subject_id === subject.id &&
          (item.status === 'ready' || item.status === 'running'),
      );
      const database = getDb();
      if (parked) {
        const moved: Widget = { ...parked, section: 'today' };
        saveWidget(database, moved);
        return { ...current, widgets: replaceById(current.widgets, moved) };
      }

      const template = current.widgets.find((item) => item.subject_id === subject.id);
      const instanceId = Crypto.randomUUID();
      const widgetId = Crypto.randomUUID();
      const when = formatLocalDateTime(now);
      const instance: Instance = {
        id: instanceId,
        subject_id: subject.id,
        when,
        status: 'prepared',
      };
      const widget: Widget = {
        id: widgetId,
        type: template?.type ?? 'tick',
        title: subject.title,
        payload:
          template?.type === 'counter'
            ? { count: 0, target: subject.target?.goal ?? template.payload.target ?? 0 }
            : template?.type === 'reminder'
              ? { fire_at: when }
              : { done: false },
        status: 'ready',
        when,
        section: 'today',
        subject_id: subject.id,
        instance_id: instanceId,
        tile_size: template?.tile_size ?? COMPACT_TILE,
        version: 1,
      };
      saveInstance(database, instance);
      saveWidget(database, widget);
      const nextSubject: Subject = {
        ...subject,
        instance_ids: [...subject.instance_ids, instanceId],
      };
      saveSubject(database, nextSubject);
      return {
        ...current,
        subjects: replaceById(current.subjects, nextSubject),
        instances: [...current.instances, instance],
        widgets: [...current.widgets, widget],
      };
    },
    [],
  );

  const answerDrift = useCallback(
    (subjectId: string, action: 'today' | 'weekly' | 'retire') => {
      const database = getDb();
      const current = loadSnapshot(database);
      const subject = current.subjects.find((item) => item.id === subjectId);
      if (!subject) return;
      const now = new Date();
      const asked = formatLocalDateTime(now);
      let next: Subject = {
        ...subject,
        last_asked: asked,
        asks_made: (subject.asks_made ?? 0) + 1,
      };
      let working = current;
      switch (action) {
        case 'today':
          working = placeSubjectOnToday(
            { ...current, subjects: replaceById(current.subjects, next) },
            next,
            now,
          );
          next = working.subjects.find((item) => item.id === subjectId) ?? next;
          break;
        case 'weekly':
          next = {
            ...next,
            cadence: { count: 1, period: 'week' },
            status: 'shrunk',
          };
          break;
        case 'retire':
          next = {
            ...next,
            cadence: { count: null, period: 'none' },
            status: 'retired',
          };
          break;
        default: {
          const exhaustive: never = action;
          return exhaustive;
        }
      }
      saveSubject(database, next);
      appendEvent(database, 'drift_answered', {
        subject_id: subject.id,
        payload: { action, asks_made: next.asks_made, last_asked: asked },
      });
      persist({
        ...working,
        subjects: replaceById(working.subjects, next),
      });
    },
    [persist, placeSubjectOnToday],
  );

  const closeMorningCard = useCallback((now = new Date()) => {
    const day = formatLocalDate(now);
    const database = getDb();
    setMeta(database, MORNING_CLOSED_META_KEY, day);
    setMorningClosedOn(day);
  }, []);

  const answerDelta = useCallback(
    (widgetId: string, action: 'yes' | 'leave' | 'later') => {
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      if (!widget) return;
      const database = getDb();
      appendEvent(database, 'delta_answered', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: widget.instance_id,
        payload: { action },
      });
      closeMorningCard();
      if (action === 'yes') {
        if (widget.type === 'tick') {
          toggleTick(widget.id);
          return;
        }
        if (widget.type === 'reminder') {
          completeReminder(widget.id);
          return;
        }
        completeCounter(widget.id);
      }
    },
    [closeMorningCard, completeCounter, completeReminder, snapshot.widgets, toggleTick],
  );

  const applyBikeDrift = useCallback(
    (days: 8 | 21) => {
      persist(restoreBikeDrift(getDb(), days));
    },
    [persist],
  );

  const value = useMemo<DeskContextValue>(
    () => ({
      ...snapshot,
      ready,
      error,
      cueFor,
      startInstance,
      markCueSurfaced,
      tickCounter,
      completeCounter,
      toggleTick,
      completeReminder,
      setReminderWindow,
      editCueText,
      editTarget,
      syncReminders,
      fireDogfoodReminder,
      noteReminderFired,
      noteReminderOpened,
      morningClosedOn,
      answerDrift,
      answerDelta,
      restoreBikeDrift: applyBikeDrift,
    }),
    [
      answerDelta,
      answerDrift,
      applyBikeDrift,
      completeCounter,
      completeReminder,
      cueFor,
      editCueText,
      editTarget,
      error,
      fireDogfoodReminder,
      markCueSurfaced,
      morningClosedOn,
      noteReminderFired,
      noteReminderOpened,
      ready,
      setReminderWindow,
      snapshot,
      startInstance,
      syncReminders,
      tickCounter,
      toggleTick,
    ],
  );

  return <DeskContext.Provider value={value}>{children}</DeskContext.Provider>;
}

export function useDesk(): DeskContextValue {
  const value = useContext(DeskContext);
  if (!value) {
    throw new Error('useDesk must be used inside DeskProvider');
  }
  return value;
}
