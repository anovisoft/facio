import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { doTimeCueFor } from '@/domain/seed';
import type { Cue, DeskSnapshot, Instance, Subject, Widget } from '@/domain/types';
import { getDb } from './database';
import {
  appendEvent,
  saveCue,
  saveInstance,
  saveSubject,
  saveWidget,
  seedIfEmpty,
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
  editCueText: (cueId: string, text: string) => void;
  editTarget: (widgetId: string, goal: number) => void;
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
  const surfacedKeys = useRef(new Set<string>());

  useEffect(() => {
    try {
      const database = getDb();
      setSnapshot(seedIfEmpty(database));
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
      const completed: Instance = { ...instance, status: 'completed' };
      saveInstance(database, completed);
      saveWidget(database, nextWidget);
      appendEvent(database, 'instance_completed', {
        subject_id: widget.subject_id,
        widget_id: widget.id,
        instance_id: instance.id,
      });
      return {
        instances: replaceById(snapshot.instances, completed),
        widgets: replaceById(snapshot.widgets, nextWidget),
        cues: applyCueIfAny(widget, cues),
      };
    },
    [applyCueIfAny, snapshot.instances],
  );

  const tickCounter = useCallback(
    (widgetId: string, delta: number) => {
      const database = getDb();
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      if (!widget || widget.type !== 'counter') return;

      const current = widget.payload.count ?? 0;
      const target = widget.payload.target ?? 0;
      const nextCount = Math.max(0, current + delta);
      const nextWidget: Widget = {
        ...widget,
        status: widget.status === 'ready' ? 'running' : widget.status,
        payload: { ...widget.payload, count: nextCount },
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

      persist({ ...snapshot, widgets: replaceById(snapshot.widgets, nextWidget), subjects });

      if (target > 0 && nextCount >= target) {
        const instance = snapshot.instances.find((item) => item.id === widget.instance_id);
        if (instance && instance.status !== 'completed') {
          const standing: Widget = { ...nextWidget, status: 'done', section: 'lifetime' };
          const finished = finishInstance(widget, instance, standing, snapshot.cues);
          persist({ ...snapshot, subjects, ...finished });
        }
      }
    },
    [finishInstance, persist, snapshot],
  );

  const completeCounter = useCallback(
    (widgetId: string) => {
      const widget = snapshot.widgets.find((item) => item.id === widgetId);
      const instance = snapshot.instances.find((item) => item.id === widget?.instance_id);
      if (!widget || !instance || instance.status === 'completed') return;
      const standing: Widget = { ...widget, status: 'done', section: 'lifetime' };
      persist({
        ...snapshot,
        ...finishInstance(widget, instance, standing, snapshot.cues),
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
        status: 'done',
        section: 'today',
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
      editCueText,
      editTarget,
    }),
    [
      completeCounter,
      cueFor,
      editCueText,
      editTarget,
      error,
      markCueSurfaced,
      ready,
      snapshot,
      startInstance,
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
