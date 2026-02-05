import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

type LogEntry = {
  path: string;
  filename: string;
  log_id: string;
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
  const [k, setK] = useState(2);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  const selectAll = () => {
    if (selected.size === logs.length) setSelected(new Set());
    else setSelected(new Set(logs.map((l) => l.path)));
  };

  const handleSubmit = async () => {
    const filenames = Array.from(selected);
    if (filenames.length === 0) {
      setError('Select at least one log file.');
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
          <h2 className="panel-title">1. Select logs</h2>
          <p className="panel-description">
            Choose feedback logs from the server. All must use the same image and
            coarseness.
          </p>
          {error && <p className="panel-error">{error}</p>}
          {logs.length === 0 ? (
            <p className="panel-hint">No log files found. Save feedback first.</p>
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
        </section>

        <section className="panel">
          <h2 className="panel-title">2. Set k</h2>
          <p className="panel-description">
            Number of trials in each combination for overlap (1 ≤ k ≤ selected
            count).
          </p>
          <input
            type="number"
            min={1}
            max={Math.max(1, selected.size)}
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
            disabled={loading || selected.size === 0}
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
