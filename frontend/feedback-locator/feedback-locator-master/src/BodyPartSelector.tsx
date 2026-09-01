import React, { useMemo } from 'react';

export type SelectionResult = {
  path: string;
  bodyPart: string;
  side: string | null;
};

interface BodyPartSelectorProps {
  /** * A record of asset names to URLs.
   * Example: { "hand-left-Left_Hand": "blob:http://..." }
   */
  assets: Record<string, string>;
  onSelect: (selection: SelectionResult) => void;
  selectedPath?: string;
}

export const BodyPartSelector: React.FC<BodyPartSelectorProps> = ({ assets, onSelect, selectedPath }) => {

  // 1. Parse the provided assets into an organized structure
  const bodyMap = useMemo(() => {
    const map: Record<string, { sides: Record<string, string>; niceName: string }> = {};

    Object.entries(assets).forEach(([key, url]) => {
      // Logic assumes key is 'part-side-Nice_Name' (from filename or glob key)
      // We strip extensions or paths if they exist in the key
      const cleanKey = key.split('/').pop()?.replace('.svg', '') || key;
      const [part, side, niceName] = cleanKey.split('-');

      const cleanSide = side === '' ? null : side;

      if (!map[part]) {
        map[part] = { sides: {}, niceName: (niceName || part).replace(/_/g, ' ') };
      }
      map[part].sides[cleanSide || 'default'] = url;
    });

    return map;
  }, [assets]);

  const parts = Object.keys(bodyMap);

  const currentSelection = useMemo(() => {
    for (const [part, data] of Object.entries(bodyMap)) {
      for (const [side, url] of Object.entries(data.sides)) {
        if (url === selectedPath) return { part, side: side === 'default' ? null : side };
      }
    }
    return null;
  }, [selectedPath, bodyMap]);

  // Selection handlers remain the same...
  const handlePartChange = (part: string) => {
    const data = bodyMap[part];
    const firstSide = Object.keys(data.sides)[0];
    onSelect({
      path: data.sides[firstSide],
      bodyPart: part,
      side: firstSide === 'default' ? null : firstSide,
    });
  };

  const handleSideChange = (side: string) => {
    if (!currentSelection) return;
    const path = bodyMap[currentSelection.part].sides[side];
    onSelect({
      path,
      bodyPart: currentSelection.part,
      side: side === 'default' ? null : side,
    });
  };

  return (
    <div style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px' }}>
      <div>
        <label>Body Part: </label>
        <select
          value={currentSelection?.part || ''}
          onChange={(e) => handlePartChange(e.target.value)}
        >
          <option value="" disabled>Select...</option>
          {parts.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {currentSelection && Object.keys(bodyMap[currentSelection.part].sides).length > 1 && (
        <div style={{ marginTop: '10px' }}>
          <label>Side: </label>
          {Object.keys(bodyMap[currentSelection.part].sides).map(side => (
            <label key={side} style={{ marginRight: '10px' }}>
              <input
                type="radio"
                checked={currentSelection.side === (side === 'default' ? null : side)}
                onChange={() => handleSideChange(side)}
              />
              {side === 'default' ? 'Center' : side}
            </label>
          ))}
        </div>
      )}
    </div>
  );
};
