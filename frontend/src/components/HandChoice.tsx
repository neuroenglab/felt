import { handImageName } from '../hooks/useTrial';

type HandImage = {
  filename: string;
  url: string;
};

type HandChoiceProps = {
  images: HandImage[];
  /** The name of the image the page shows now. */
  selected: string | null;
  onPick: (image: HandImage) => void;
};

const SIDES: { side: string; label: string }[] = [
  { side: 'left', label: 'Left hand' },
  { side: 'right', label: 'Right hand' },
];

/**
 * The two hand images of the linked page. The uploaded images are named
 * `hand-left-*.svg` and `hand-right-*.svg`; a missing one disables its button.
 */
export function HandChoice({ images, selected, onPick }: HandChoiceProps) {
  const names = images.map((img) => img.filename);
  return (
    <div className="hand-choice">
      {SIDES.map(({ side, label }) => {
        const name = handImageName(side, names);
        const image = images.find((img) => img.filename === name);
        const active = name !== null && name === selected;
        return (
          <button
            key={side}
            type="button"
            className={`secondary-button hand-choice-button${active ? ' hand-choice-active' : ''}`}
            disabled={!image}
            onClick={() => image && onPick(image)}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
