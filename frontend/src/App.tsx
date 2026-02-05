import { useState } from 'react';
import './App.css';

import {
  FeedbackLocator,
  type SensationLocation,
} from '@neuroenglab/nel-feedback-ui';

import { SvgFilePicker } from './components/SvgFilePicker';

function App() {
  const [feedbackLocation, setFeedbackLocation] = useState<SensationLocation | undefined>(undefined);
  const [customSvg, setCustomSvg] = useState<string | null>(null);
  const [selectedImageName, setSelectedImageName] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 2000); // Disappears after 2000ms
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

    const rawName = selectedImageName ?? customSvg ?? '';
    const baseName = rawName.split(/[/\\]/).pop() ?? rawName;
    const image_path = baseName;

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
      const response = await fetch('/api/save-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error('Failed to save');

      const result = await response.json();
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

  return (
    <div className="app-root">
      <header className="app-header">
        <div>
          <h1 className="app-title">Perception Feedback Tool</h1>
          <p className="app-subtitle">Load a body-part SVG and mark perceived sensations.</p>
        </div>
      </header>

      <main className="app-main">
        {!customSvg ? (
          <section className="panel panel-picker">
            <h2 className="panel-title">1. Choose body image</h2>
            <p className="panel-description">
              Select a single SVG file from your computer. This will be used as the canvas for marking sensation locations.
            </p>
            <SvgFilePicker
              onSelect={({ imageUrl, originalName }) => {
                setCustomSvg(imageUrl);
                setSelectedImageName(originalName);
                setFeedbackLocation(undefined);
              }}
            />
          </section>
        ) : (
          <section className="panel panel-locator">
            <div className="panel-header-row">
              <div>
                <h2 className="panel-title">2. Mark sensation locations</h2>
                {selectedImageName && (
                  <p className="panel-file-label">Current image: {selectedImageName}</p>
                )}
              </div>
              <div className="panel-actions">
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
              </div>
            </div>

            <div className="locator-wrapper">
              <FeedbackLocator
                imageSrc={customSvg}
                feedbackLocation={feedbackLocation}
                onUpdate={(loc) => setFeedbackLocation(loc)}
                coarseness={80}
              />
            </div>
          </section>
        )}
      </main>

      {toast && (
        <div
          className={`toast toast-${toast.type}`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default App;
