import { useEffect, useState } from 'react';

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
};

/**
 * Read the trial of the console once per interval.
 *
 * Null until the first answer arrives, so the page shows no banner before it
 * knows whether FELT is linked.
 */
export function useTrial(intervalMs = 1000): TrialInfo | null {
  const [trial, setTrial] = useState<TrialInfo | null>(null);

  useEffect(() => {
    let stopped = false;

    const read = () => {
      fetch('api/trial')
        .then((res) => res.json())
        .then((data: TrialInfo) => {
          if (!stopped) setTrial(data);
        })
        .catch(() => {
          // The FELT service itself did not answer. Keep what we know, and
          // report the link as down so the page locks the drawing surface.
          if (!stopped) {
            setTrial((prev) =>
              prev && prev.linked ? { ...prev, reachable: false, can_draw: false } : prev,
            );
          }
        });
    };

    read();
    const timer = window.setInterval(read, intervalMs);
    return () => {
      stopped = true;
      window.clearInterval(timer);
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

/** The uploaded image of the console hand, by the `hand-{hand}-` name rule. */
export function handImageName(hand: string | null | undefined, names: string[]): string | null {
  if (!hand) return null;
  const prefix = `hand-${hand.toLowerCase()}-`;
  return names.find((name) => name.toLowerCase().startsWith(prefix)) ?? null;
}
