import type { Subject } from './types';

const TITLES: Record<string, string> = {
  'push-ups': 'Отжимания',
  bike: 'Велосипед',
  vegetables: 'Овощи',
};

export function displayTitle(subject: Subject | undefined, fallback = 'Практика'): string {
  if (!subject) return fallback;
  return TITLES[subject.id] ?? subject.title;
}

function daysWord(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return 'день';
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'дня';
  return 'дней';
}

export function driftCardText(title: string, silentDays: number): string {
  return `${title} не случался ${silentDays} ${daysWord(silentDays)}. На сегодня, раз в неделю или убрать?`;
}

export function deltaCardText(title: string): string {
  return `${title} не отмечены — сделал подход?`;
}
