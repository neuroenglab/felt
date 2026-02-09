import React, { useRef } from 'react';

type SvgFilePickerProps = {
  onSelect: (selection: { imageUrl: string; originalName: string }) => void;
};

export function SvgFilePicker({ onSelect }: SvgFilePickerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange: React.ChangeEventHandler<HTMLInputElement> = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Only allow SVG files
    if (file.type !== 'image/svg+xml' && !file.name.toLowerCase().endsWith('.svg')) {
      alert('Please select an SVG file.');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/upload-image', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? 'Failed to upload SVG');
      }

      const imageUrl: string = data.url ?? `/uploads/${data.filename}`;
      const originalName: string = data.filename ?? file.name;

      onSelect({ imageUrl, originalName });
    } catch (err) {
      console.error(err);
      alert('Failed to upload SVG to server.');
    } finally {
      // Reset input so the same file can be selected again if needed
      if (event.target) {
        event.target.value = '';
      }
    }
  };

  return (
    <div className="card">
      <h2>Choose an SVG body image</h2>
      <p>
        Select an svg containing a non-transparent body part on a transparent background.
      </p>
      <button type="button" onClick={handleClick}>
        Select SVG file…
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/svg+xml"
        style={{ display: 'none' }}
        onChange={handleChange}
      />
    </div>
  );
}

