import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';

type LogEntry = {
  path: string;
  filename: string;
  log_id: string;
};

type UploadedEntry = {
  path: string;
  filename: string;
};

type ProcessResult = {
  status: string;
  stability_score: number;
  stable_overlap_area: number;
  best_day_area: number;
  max_area_file: string;
  best_combination: string[] | null;
};

export function ProcessFeedbackPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploaded, setUploaded] = useState<UploadedEntry[]>([]);
  const [selectedUploaded, setSelectedUploaded] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [k, setK] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const totalPaths = [
    ...Array.from(selected),
    ...uploaded.filter((u) => selectedUploaded.has(u.path)).map((u) => u.path),
  ];

  useEffect(() => {
    fetch('/api/logs')
      .then((res) => res.json())
      .then((data: { logs: LogEntry[] }) => {
        setLogs(data.logs ?? []);
      })
      .catch((err) => setError('Failed to load logs: ' + String(err)));
  }, []);

  const toggle = (path: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const removeUploaded = (path: string) => {
    setUploaded((prev) => prev.filter((u) => u.path !== path));
    setSelectedUploaded((prev) => {
      const next = new Set(prev);
      next.delete(path);
      return next;
    });
  };

  const toggleUploaded = (path: string) => {
    setSelectedUploaded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const selectAllUploaded = () => {
    if (selectedUploaded.size === uploaded.length) setSelectedUploaded(new Set());
    else setSelectedUploaded(new Set(uploaded.map((u) => u.path)));
  };

  const selectAll = () => {
    if (selected.size === logs.length) setSelected(new Set());
    else setSelected(new Set(logs.map((l) => l.path)));
  };

  const uploadFiles = useCallback(async (files: FileList | File[]) => {
    const arr = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.json'));
    if (arr.length === 0) return;

    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      arr.forEach((f) => formData.append('files', f));

      const res = await fetch('/api/upload-logs', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Upload failed');

      const newEntries: UploadedEntry[] = (data.uploads ?? []).map(
        (u: { path: string; filename: string }) => ({ path: u.path, filename: u.filename })
      );
      setUploaded((prev) => [...prev, ...newEntries]);
      setSelectedUploaded((prev) => new Set([...prev, ...newEntries.map((u) => u.path)]));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer?.files?.length) uploadFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files?.length) uploadFiles(files);
    e.target.value = '';
  };

  const handleSubmit = async () => {
    const filenames = totalPaths;
    if (filenames.length === 0) {
      setError('Select or upload at least one log file.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch('/api/process-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filenames, k }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail ?? 'Process failed');
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div>
          <h1 className="app-title">Process Feedback</h1>
          <p className="app-subtitle">
            Select log files and compute stability across trials.
          </p>
        </div>
        <Link to="/" className="secondary-button">
          ← Mark sensations
        </Link>
      </header>

      <main className="app-main">
        <section className="panel">
          <h2 className="panel-title">1. Add logs</h2>
          <p className="panel-description">
            Choose from server logs or upload JSON files. All must use the same image and
            coarseness.
          </p>
          {error && <p className="panel-error">{error}</p>}

          <div
            className={`drop-zone ${dragActive ? 'drop-zone-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              multiple
              onChange={handleFileInput}
              className="drop-zone-input"
              disabled={uploading}
            />
            {uploading ? (
              <span>Uploading…</span>
            ) : (
              <>
                <span className="drop-zone-text">Drag & drop JSON files here</span>
                <span className="drop-zone-hint">or click to browse</span>
              </>
            )}
          </div>

          {uploaded.length > 0 && (
            <div className="uploaded-section">
              <div className="uploaded-section-header">
                <h3 className="uploaded-title">Uploaded ({uploaded.length})</h3>
                <button
                  type="button"
                  className="secondary-button secondary-button-small"
                  onClick={selectAllUploaded}
                >
                  {selectedUploaded.size === uploaded.length ? 'Deselect all' : 'Select all'}
                </button>
              </div>
              <ul className="log-list">
                {uploaded.map((u) => (
                  <li key={u.path} className="log-list-item-uploaded">
                    <label className="log-list-item-uploaded-label">
                      <input
                        type="checkbox"
                        checked={selectedUploaded.has(u.path)}
                        onChange={() => toggleUploaded(u.path)}
                      />
                      <span className="log-id">{u.filename}</span>
                    </label>
                    <button
                      type="button"
                      className="log-remove"
                      onClick={() => removeUploaded(u.path)}
                      title="Remove"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="server-logs-section">
            <div className="server-logs-header">
              <h3 className="uploaded-title">Server logs</h3>
              <button
                type="button"
                className="secondary-button secondary-button-small"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                Upload files
              </button>
            </div>
            {logs.length === 0 ? (
              <p className="panel-hint">No log files found. Save feedback first or upload files above.</p>
            ) : (
              <>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={selectAll}
                  style={{ marginBottom: 12 }}
                >
                  {selected.size === logs.length ? 'Deselect all' : 'Select all'}
                </button>
                <ul className="log-list">
                  {logs.map((log) => (
                    <li key={log.path}>
                      <label>
                        <input
                          type="checkbox"
                          checked={selected.has(log.path)}
                          onChange={() => toggle(log.path)}
                        />
                        <span className="log-id">{log.log_id}</span>
                        <span className="log-filename">{log.filename}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </section>

        <section className="panel">
          <h2 className="panel-title">2. Set k</h2>
          <p className="panel-description">
            Number of trials in each combination for overlap (1 ≤ k ≤ total count).
          </p>
          <input
            type="number"
            min={1}
            max={Math.max(1, totalPaths.length)}
            value={k}
            onChange={(e) => setK(Number(e.target.value) || 1)}
            className="k-input"
          />
        </section>

        <section className="panel">
          <button
            type="button"
            className="primary-button"
            onClick={handleSubmit}
            disabled={loading || totalPaths.length === 0}
          >
            {loading ? 'Processing…' : 'Process feedback'}
          </button>

          {result && (
            <div className="process-result">
              <h3>Results</h3>
              <dl>
                <dt>Stability score</dt>
                <dd>{(result.stability_score * 100).toFixed(1)}%</dd>
                <dt>Stable overlap area (px²)</dt>
                <dd>{result.stable_overlap_area.toFixed(1)}</dd>
                <dt>Best day area (px²)</dt>
                <dd>{result.best_day_area.toFixed(1)}</dd>
                <dt>Max area file</dt>
                <dd>{result.max_area_file}</dd>
                {result.best_combination && result.best_combination.length > 0 && (
                  <>
                    <dt>Best combination</dt>
                    <dd>{result.best_combination.join(', ')}</dd>
                  </>
                )}
              </dl>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
