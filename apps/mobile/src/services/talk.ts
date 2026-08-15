import type { Cue, Subject, TalkResult, Widget } from '@/domain/types';

export class TalkRequestError extends Error {
  readonly reason: 'no_api_url' | 'network' | 'no_key' | 'invalid' | 'http';
  readonly status: number | null;

  constructor(reason: TalkRequestError['reason'], message: string, status: number | null = null) {
    super(message);
    this.reason = reason;
    this.status = status;
  }
}

function apiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/$/, '');
}

export async function requestTurn(input: {
  utterance: string;
  subject: Subject;
  cues: Cue[];
  widget: Widget;
}): Promise<TalkResult> {
  const base = apiBaseUrl();
  if (!base) {
    throw new TalkRequestError('no_api_url', 'нет адреса сервиса');
  }

  let response: Response;
  try {
    response = await fetch(`${base}/v1/turns`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        utterance: input.utterance,
        subject: input.subject,
        cues: input.cues,
        widget: input.widget,
      }),
    });
  } catch {
    throw new TalkRequestError('network', 'сервис недоступен');
  }

  if (response.status === 501) {
    throw new TalkRequestError('no_key', 'сервис без ключа', 501);
  }
  if (response.status === 422) {
    throw new TalkRequestError('invalid', 'так не записывается', 422);
  }
  if (!response.ok) {
    throw new TalkRequestError('http', 'сервис не принял', response.status);
  }

  const body = (await response.json()) as TalkResult;
  if (!body || typeof body.confirmation !== 'string' || !Array.isArray(body.patches)) {
    throw new TalkRequestError('invalid', 'так не записывается');
  }
  return body;
}
