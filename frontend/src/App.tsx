import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import './App.css';

import {
  FeedbackLocator,
  type SensationLocation,
} from '@neuroenglab/nel-feedback-ui';

import { SvgFilePicker } from './components/SvgFilePicker';
import { ProcessFeedbackPage } from './pages/ProcessFeedbackPage';

type BodyImage = {
  filename: string;
  url: string;
};

function MarkSensationsPage() {
  const [feedbackLocation, setFeedbackLocation] = useState<SensationLocation | undefined>(undefined);
  const [customSvg, setCustomSvg] = useState<string | null>(null);
  const [selectedImageName, setSelectedImageName] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [availableImages, setAvailableImages] = useState<BodyImage[]>([]);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 2000); // Disappears after 2000ms
  };

  useEffect(() => {
    fetch('/api/images')
      .then((res) => res.json())
      .then((data: { images: BodyImage[] }) => {
        setAvailableImages(data.images ?? []);
      })
      .catch((err) => {
        console.error('Failed to load body images', err);
      });
  }, []);

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
        <Link to="/process" className="secondary-button">
          Process feedback →
        </Link>
      </header>

      <main className="app-main">
        {!customSvg && (
          <section className="panel panel-picker">
            <h2 className="panel-title">1. Choose body image</h2>
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
                <ul className="log-list">
                  {availableImages.map((img) => (
                    <li key={img.filename}>
                      <button
                        type="button"
                        className="secondary-button secondary-button-small"
                        onClick={() => {
                          setCustomSvg(img.url);
                          setSelectedImageName(img.filename);
                          setFeedbackLocation(undefined);
                        }}
                      >
                        {img.filename}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {customSvg && (
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
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MarkSensationsPage />} />
        <Route path="/process" element={<ProcessFeedbackPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
