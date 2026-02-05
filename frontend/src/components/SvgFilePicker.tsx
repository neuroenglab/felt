import React, { useRef } from 'react';

type SvgFilePickerProps = {
  onSelect: (selection: { imageUrl: string; originalName: string }) => void;
};

export function SvgFilePicker({ onSelect }: SvgFilePickerProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange: React.ChangeEventHandler<HTMLInputElement> = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Only allow SVG files
    if (file.type !== 'image/svg+xml' && !file.name.toLowerCase().endsWith('.svg')) {
      alert('Please select an SVG file.');
      return;
    }

    const url = URL.createObjectURL(file);
    const originalName = file.name;
    onSelect({ imageUrl: url, originalName });
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

