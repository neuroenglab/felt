import { useEffect, useRef, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import './App.css';

import {
  FeedbackLocator,
  type SensationLocation,
} from '@neuroenglab/nel-feedback-ui';

import { HandChoice } from './components/HandChoice';
import { SvgFilePicker } from './components/SvgFilePicker';
import { TrialBanner } from './components/TrialBanner';
import { trialBanner, useTrial } from './hooks/useTrial';
import { handImage, type HandImage } from './hands';
import { ProcessFeedbackPage } from './pages/ProcessFeedbackPage';

type BodyImage = {
  filename: string;
  url: string;
};

// The brush colour of a target painting.
const TARGET_COLOR = 'rgba(22, 163, 74, 0.55)';
// The colour and the opacity of the target underlay.
const UNDERLAY_COLOR = '#16a34a';
const UNDERLAY_OPACITY = 0.3;

/** What the console answered to a sent painting, through the FELT service. */
type ConsoleAnswer = {
  accepted: boolean;
  regions: string[];
  problem: string | null;
  reason: string | null;
};

/** The answer of `POST /api/save-feedback`. */
type SaveAnswer = {
  filename: string;
  console?: ConsoleAnswer;
};

function isConsoleAnswer(value: unknown): value is ConsoleAnswer {
  if (typeof value !== 'object' || value === null) return false;
  const fields = value as Record<string, unknown>;
  const isText = (text: unknown) => text === null || text === undefined || typeof text === 'string';
  return (
    typeof fields.accepted === 'boolean' &&
    Array.isArray(fields.regions) &&
    fields.regions.every((region) => typeof region === 'string') &&
    isText(fields.problem) &&
    isText(fields.reason)
  );
}

function isSaveAnswer(value: unknown): value is SaveAnswer {
  if (typeof value !== 'object' || value === null) return false;
  const fields = value as Record<string, unknown>;
  if (typeof fields.filename !== 'string') return false;
  return fields.console === undefined || isConsoleAnswer(fields.console);
}

function MarkSensationsPage() {
  const [feedbackLocation, setFeedbackLocation] = useState<SensationLocation | undefined>(undefined);
  const [customSvg, setCustomSvg] = useState<string | null>(null);
  const [selectedImageName, setSelectedImageName] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [availableImages, setAvailableImages] = useState<BodyImage[]>([]);
  const [sending, setSending] = useState(false);
  // The target of the run, under the painting. It is read-only and not exported.
  const [underlay, setUnderlay] = useState<{ key: string; location: SensationLocation } | null>(
    null,
  );
  // What the subject reports beside the painting of a sensation.
  const [pain, setPain] = useState(false);
  const [intensity, setIntensity] = useState<number | null>(null);

  const trial = useTrial(1000);
  const linked = trial?.linked === true;
  // No sequence runs: the linked page behaves as the unlinked one.
  const manual = linked && trial?.manual === true;
  // A sequence runs, so the console owns the hand, the drawing and the send.
  const inSequence = linked && !manual;
  // Without the console link the page draws and exports as it always did.
  const canDraw = !linked || trial?.can_draw === true;
  // The subject paints the target of the run, not the sensation of a trial.
  const paintingTarget = inSequence && trial?.purpose === 'target';
  // The subject paints a sensation and reports the pain and the intensity.
  const paintingSensation = inSequence && trial?.purpose === 'sensation';
  const hand = trial?.hand ?? null;
  const trialId = trial?.trial_id ?? null;
  // The sequence the console runs now, and the trial inside it.
  const sequenceKey =
    inSequence && trial?.reachable
      ? `${trial.subject_code ?? ''}/${trial.sequence_id ?? ''}`
      : null;
  const trialKey = `${trial?.subject_code ?? ''}/${trial?.sequence_id ?? ''}/${trialId ?? ''}`;
  // The run the underlay belongs to. It is null in manual mode and off the link.
  const underlayKey = inSequence
    ? `${trial?.subject_code ?? ''}/${trial?.sequence_id ?? ''}`
    : null;
  // The target the console reports for the run.
  const consoleTarget = trial?.target?.feedbackLocation ?? null;
  const pickedSequence = useRef<string | null>(null);

  const refreshImages = () => {
    fetch('api/images')
      .then((res) => res.json())
      .then((data: { images: BodyImage[] }) => {
        setAvailableImages(data.images ?? []);
      })
      .catch((err) => console.error('Failed to load body images', err));
  };

  const showToast = (message: string, type: 'success' | 'error' = 'success', ms = 2000) => {
    setToast({ message, type });
    setTimeout(() => setToast(null), ms); // Disappears after 2000ms by default
  };

  useEffect(() => {
    refreshImages();
  }, []);

  // The console owns the hand of a sequence, so a new sequence opens on its
  // image. Inside a sequence the subject keeps the image it chose.
  useEffect(() => {
    if (!sequenceKey || sequenceKey === pickedSequence.current) return;
    const image = handImage(hand);
    if (!image) return;
    pickedSequence.current = sequenceKey;
    setCustomSvg(image.url);
    setSelectedImageName(image.filename);
    setFeedbackLocation(undefined);
  }, [sequenceKey, hand]);

  // A new trial clears the painting, the pain and the intensity.
  useEffect(() => {
    setFeedbackLocation((prev) => (prev ? { ...prev, chosenPoints: { row: [], col: [] } } : prev));
    setPain(false);
    setIntensity(null);
  }, [trialKey]);

  // A new run, or the end of the sequence, drops the underlay.
  useEffect(() => {
    setUnderlay((prev) => (prev && prev.key === underlayKey ? prev : null));
  }, [underlayKey]);

  // The page takes the target of the console when it has none of its own.
  useEffect(() => {
    if (!underlayKey || !consoleTarget) return;
    setUnderlay((prev) =>
      prev && prev.key === underlayKey ? prev : { key: underlayKey, location: consoleTarget },
    );
  }, [underlayKey, consoleTarget]);

  const pickImage = (image: BodyImage | HandImage) => {
    setCustomSvg(image.url);
    setSelectedImageName(image.filename);
    setFeedbackLocation(undefined);
  };

  const currentImageName = () => {
    const rawName = selectedImageName ?? customSvg ?? '';
    return rawName.split(/[/\\]/).pop() ?? rawName;
  };

  const exportFeedbackLog = async () => {
    if (!feedbackLocation) {
      showToast('Mark a sensation first!', 'error');
      return;
    }

    // 1. Prompt for Log ID (e.g., Subject001 or Trial_A)
    const logId = prompt("Please enter a Log ID (Subject or Trial name):", "Subject_001");

    // If the user clicks "Cancel" or leaves it empty, stop the export
    if (logId === null || logId.trim() === "") {
      showToast('Export cancelled: Log ID is required', 'error');
      return;
    }

    const image_path = currentImageName();

    const payload = {
      log_id: logId.trim(), // Adding the ID here
      filename: image_path,
      feedbackLocation: {
        ...feedbackLocation,
        image_path: image_path,
        exported_at: new Date().toISOString()
      }
    };

    try {
      const response = await fetch('api/save-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error('Failed to save');

      const result: unknown = await response.json();
      if (!isSaveAnswer(result)) throw new Error('The service answered an unknown shape');
      // Clear current drawing after successful save
      setFeedbackLocation({
        ...feedbackLocation,
        chosenPoints: { row: [], col: [] }
      });
      showToast(`Success! Saved ${logId} to ${result.filename}`);
    } catch (err) {
      console.error(err);
      showToast('Error saving to server', 'error');
    }
  };

  /**
   * Send the painting for the trial the console names. `felt` false is the
   * answer Nothing felt: an empty painting, with no drawing needed. The
   * painting stays on the screen, so the subject can correct it and send
   * again while the console scores the same trial.
   */
  const sendForTrial = async (felt: boolean) => {
    if (!trial || !trial.trial_id || trial.can_draw !== true) {
      showToast(trial ? trialBanner(trial).text : 'No trial to score', 'error');
      return;
    }
    if (felt && (!feedbackLocation || feedbackLocation.chosenPoints.row.length === 0)) {
      showToast('Mark a sensation first!', 'error');
      return;
    }

    const image_path = currentImageName();
    const location: SensationLocation = feedbackLocation
      ? { ...feedbackLocation, image_path }
      : {
          image_path,
          image_size: { w: 0, h: 0 },
          segment_size_px: { w: 0, h: 0 },
          coarsenessPercent: 80,
          chosenPoints: { row: [], col: [] },
        };

    const payload = {
      log_id: trial.subject_code ?? '',
      filename: image_path,
      feedbackLocation: felt ? location : { ...location, chosenPoints: { row: [], col: [] } },
      trial: {
        subject_code: trial.subject_code ?? '',
        sequence_id: trial.sequence_id ?? '',
        trial_id: trial.trial_id,
      },
      felt,
      // A target carries no report. Nothing felt carries the pain and no intensity.
      ...(paintingTarget ? {} : { pain, intensity: felt ? intensity : null }),
    };

    setSending(true);
    try {
      const response = await fetch('api/save-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('Failed to save');

      const result: unknown = await response.json();
      if (!isSaveAnswer(result)) throw new Error('The service answered an unknown shape');
      const answer = result.console;
      if (answer && answer.accepted && !answer.problem) {
        const regions = answer.regions.length > 0 ? answer.regions.join(', ') : 'no region';
        // The accepted target becomes the underlay of the run.
        if (paintingTarget) setUnderlay({ key: underlayKey ?? trialKey, location });
        showToast(
          paintingTarget
            ? `Sent the target: ${regions}`
            : `Sent for trial ${trial.trial_id}: ${regions}`,
          'success',
          3000,
        );
      } else if (answer) {
        showToast(
          answer.problem ?? answer.reason ?? 'The console refused the painting',
          'error',
          3000,
        );
      } else {
        showToast(`Saved ${result.filename}`, 'success', 3000);
      }
    } catch (err) {
      console.error(err);
      showToast('Error saving to server', 'error');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div>
          <h1 className="app-title">Perception Feedback Tool</h1>
          <p className="app-subtitle">Load a body-part SVG and mark perceived sensations.</p>
        </div>
        <Link to="/process" className="secondary-button">
          Process feedback →
        </Link>
      </header>

      {linked && trial && <TrialBanner trial={trial} imageName={selectedImageName} />}

      <main className="app-main">
        {!customSvg && (
          <section className="panel panel-picker">
            <h2 className="panel-title">1. Choose body image</h2>
            {inSequence ? (
              <>
                <p className="panel-description">Choose the hand of the session.</p>
                <HandChoice selected={selectedImageName} onPick={pickImage} />
              </>
            ) : (
              <>
              <p className="panel-description">
                Select an SVG file from your computer or choose from previously uploaded images.
              </p>
              <SvgFilePicker
                onSelect={({ imageUrl, originalName }) => {
                  setCustomSvg(imageUrl);
                  setSelectedImageName(originalName);
                  setFeedbackLocation(undefined);
                }}
              />

              {availableImages.length > 0 && (
                <div style={{ marginTop: '1.5rem' }}>
                  <h3 className="panel-subtitle">Previously uploaded images</h3>
                  <ul className="log-list body-parts-list">
                    {availableImages.map((img) => (
                      <li key={img.filename} className="body-parts-list-item">
                        <button
                          type="button"
                          className="secondary-button secondary-button-small body-part-button"
                          onClick={() => {
                            setCustomSvg(img.url);
                            setSelectedImageName(img.filename);
                            setFeedbackLocation(undefined);
                          }}
                        >
                          {img.filename}
                        </button>
                        <button
                          type="button"
                          className="body-part-remove"
                          onClick={() => {
                            if (!window.confirm(`Delete "${img.filename}"? This cannot be undone.`)) return;
                            fetch(`api/images/${encodeURIComponent(img.filename)}`, { method: 'DELETE' })
                              .then((res) => {
                                if (!res.ok) return res.json().then((d) => Promise.reject(new Error(d.detail ?? 'Delete failed')));
                                return res.json();
                              })
                              .then(() => {
                                refreshImages();
                                if (selectedImageName === img.filename) {
                                  setCustomSvg(null);
                                  setSelectedImageName(null);
                                  setFeedbackLocation(undefined);
                                }
                                showToast('Image deleted');
                              })
                              .catch((err) => showToast(err instanceof Error ? err.message : 'Delete failed', 'error'));
                          }}
                          title="Delete this image"
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              </>
            )}
          </section>
        )}

        {customSvg && (
          <section className="panel panel-locator">
            <div className="panel-header-row">
              <div>
                <h2 className="panel-title">
                  {paintingTarget ? '2. Paint the target' : '2. Mark sensation locations'}
                </h2>
                {selectedImageName && (
                  <p className="panel-file-label">Current image: {selectedImageName}</p>
                )}
              </div>
              <div className="panel-actions">
                {inSequence ? (
                  <>
                    <HandChoice selected={selectedImageName} onPick={pickImage} />
                    {paintingSensation && (
                      <div className="report-controls">
                        <button
                          type="button"
                          className={`report-pain${pain ? ' report-pain-on' : ''}`}
                          aria-pressed={pain}
                          onClick={() => setPain((was) => !was)}
                        >
                          Pain {pain ? 'on' : 'off'}
                        </button>
                        <div className="report-intensity" role="group" aria-label="Intensity">
                          <span className="report-intensity-label">
                            Intensity: {intensity === null ? 'not set' : intensity}
                          </span>
                          <div className="report-intensity-scale">
                            {Array.from({ length: 11 }, (_, step) => (
                              <button
                                key={step}
                                type="button"
                                className={`report-step${intensity === step ? ' report-step-on' : ''}`}
                                aria-pressed={intensity === step}
                                // A second press on the chosen step unsets it.
                                onClick={() =>
                                  setIntensity((was) => (was === step ? null : step))
                                }
                              >
                                {step}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    {!paintingTarget && (
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={!canDraw || sending}
                        onClick={() => sendForTrial(false)}
                      >
                        Nothing felt
                      </button>
                    )}
                    <button
                      type="button"
                      className="primary-button"
                      disabled={!canDraw || sending}
                      onClick={() => sendForTrial(true)}
                    >
                      {paintingTarget
                        ? 'Send the target'
                        : trialId
                          ? `Send for trial ${trialId}`
                          : 'Send'}
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        setCustomSvg(null);
                        setSelectedImageName(null);
                        setFeedbackLocation(undefined);
                      }}
                    >
                      Choose another SVG
                    </button>
                    <button
                      type="button"
                      className="primary-button"
                      onClick={exportFeedbackLog}
                    >
                      Export drawing log
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="locator-wrapper">
              <FeedbackLocator
                imageSrc={customSvg}
                feedbackLocation={feedbackLocation}
                onUpdate={(loc) => setFeedbackLocation(loc)}
                coarseness={80}
                paintColor={paintingTarget ? TARGET_COLOR : undefined}
                underlay={
                  underlay
                    ? {
                        location: underlay.location,
                        color: UNDERLAY_COLOR,
                        opacity: UNDERLAY_OPACITY,
                      }
                    : undefined
                }
              />
              {linked && trial && !canDraw && (
                <div className="locator-lock">
                  <span className="locator-lock-text">{trialBanner(trial).text}</span>
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route path="/" element={<MarkSensationsPage />} />
        <Route path="/process" element={<ProcessFeedbackPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
