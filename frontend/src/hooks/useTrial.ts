import { useEffect, useState } from 'react';

import type { SensationLocation } from '@neuroenglab/nel-feedback-ui';

/** The answer of `GET /api/trial` of the FELT service. */
export type TrialInfo = {
  /** False when FELT runs without a console address; the page works as before. */
  linked: boolean;
  reachable?: boolean;
  state?: string | null;
  sentence?: string | null;
  subject_code?: string | null;
  sequence_id?: string | null;
  trial_id?: string | null;
  pass_index?: number | null;
  trial_saved?: boolean;
  felt_answered?: boolean;
  hand?: string | null;
  /** True in IDLE: no sequence runs, and the page works on its own. */
  manual?: boolean;
  /** True in the manual mode, and while the console scores the trial. */
  can_draw?: boolean;
  /** What the painting is for: the target of the run, or the sensation of a trial. */
  purpose?: 'target' | 'sensation' | null;
  /** The target the console accepted for this run. */
  target?: { feedbackLocation: SensationLocation } | null;
};

const isText = (value: unknown): boolean =>
  value === undefined || value === null || typeof value === 'string';

const isFlag = (value: unknown): boolean => value === undefined || typeof value === 'boolean';

const isCount = (value: unknown): boolean =>
  value === undefined || value === null || typeof value === 'number';

/** True when the target is an object, null, or absent. */
const isTarget = (value: unknown): boolean =>
  value === undefined || value === null || (typeof value === 'object' && !Array.isArray(value));

/** True when the answer carries the fields the page reads, with their types. */
function isTrialInfo(value: unknown): value is TrialInfo {
  if (typeof value !== 'object' || value === null) return false;
  const fields = value as Record<string, unknown>;
  if (typeof fields.linked !== 'boolean') return false;
  if (!fields.linked) return true;
  return (
    isFlag(fields.reachable) &&
    isText(fields.state) &&
    isText(fields.subject_code) &&
    isText(fields.sequence_id) &&
    isText(fields.trial_id) &&
    isCount(fields.pass_index) &&
    isFlag(fields.trial_saved) &&
    isFlag(fields.felt_answered) &&
    isText(fields.hand) &&
    isFlag(fields.manual) &&
    isFlag(fields.can_draw) &&
    isText(fields.purpose) &&
    isTarget(fields.target)
  );
}

/**
 * Read the trial of the console once per interval.
 *
 * Null until the first good answer arrives, so the page shows no banner before
 * it knows whether FELT is linked. A late, failed or malformed answer never
 * unlinks a page that was linked; it reports the console as not reachable, and
 * the page locks the drawing surface.
 */
export function useTrial(intervalMs = 1000): TrialInfo | null {
  const [trial, setTrial] = useState<TrialInfo | null>(null);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const clientId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    const clientUrl = `api/clients/${clientId}`;
    const heartbeat = () => { void fetch(clientUrl, {method: 'PUT'}).catch(() => {}); };
    const disconnect = () => { void fetch(clientUrl, {method: 'DELETE', keepalive: true}).catch(() => {}); };
    heartbeat();
    const heartbeatTimer = window.setInterval(heartbeat, 2000);
    window.addEventListener('pagehide', disconnect);
    // A slow answer must not overwrite a newer one.
    let generation = 0;
    const inFlight = new Set<AbortController>();

    const reportDown = () => {
      setTrial((prev) =>
        prev && prev.linked ? { ...prev, reachable: false, can_draw: false } : prev,
      );
    };

    const read = async () => {
      const mine = ++generation;
      const controller = new AbortController();
      inFlight.add(controller);
      try {
        const response = await fetch('api/trial?wait=25', { signal: controller.signal });
        if (!response.ok) throw new Error(`api/trial answered ${response.status}`);
        const data: unknown = await response.json();
        if (stopped || mine !== generation) return;
        if (isTrialInfo(data)) {
          setTrial(data);
        } else {
          reportDown();
        }
      } catch {
        if (stopped || mine !== generation) return;
        reportDown();
      } finally {
        inFlight.delete(controller);
        if (!stopped) timer = window.setTimeout(() => void read(), intervalMs);
      }
    };

    void read();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      window.clearInterval(heartbeatTimer);
      window.removeEventListener('pagehide', disconnect);
      disconnect();
      inFlight.forEach((controller) => controller.abort());
      inFlight.clear();
    };
  }, [intervalMs]);

  return trial;
}

export type BannerTone = 'ready' | 'wait' | 'idle' | 'down';

/** The banner line for the trial, and its colour. */
export function trialBanner(trial: TrialInfo): { text: string; tone: BannerTone } {
  if (trial.reachable === false) {
    return { text: 'Console not reachable', tone: 'down' };
  }
  if (trial.manual) {
    return { text: 'No sequence, manual mode', tone: 'idle' };
  }
  if (trial.can_draw && trial.purpose === 'target') {
    return {
      text:
        `Subject ${trial.subject_code ?? '?'} · paint the target` +
        ` · ${trial.sentence ?? 'draw and send'}`,
      tone: 'ready',
    };
  }
  if (trial.can_draw) {
    return {
      text:
        `Subject ${trial.subject_code ?? '?'} · trial ${trial.trial_id ?? '?'}` +
        ` · pass ${trial.pass_index ?? 0} · draw and send`,
      tone: 'ready',
    };
  }
  if (trial.state === 'STIMULATING') {
    return { text: 'Wait, stimulating', tone: 'wait' };
  }
  return { text: 'No trial to score', tone: 'idle' };
}

/** True when the chosen image shows the other hand than the console hand. */
export function isOtherHand(trial: TrialInfo, imageName: string | null): boolean {
  const hand = trial.hand;
  if (!hand || !imageName) return false;
  const other = hand === 'left' ? 'right' : 'left';
  const name = imageName.toLowerCase();
  return name.includes(other) && !name.includes(hand);
}
