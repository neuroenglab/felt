import { HAND_IMAGES, type HandImage } from '../hands';

type HandChoiceProps = {
  /** The name of the image the page shows now. */
  selected: string | null;
  onPick: (image: HandImage) => void;
};

/** The two hand images of the linked page, Left hand and Right hand. */
export function HandChoice({ selected, onPick }: HandChoiceProps) {
  return (
    <div className="hand-choice">
      {HAND_IMAGES.map((image) => (
        <button
          key={image.side}
          type="button"
          className={
            'secondary-button hand-choice-button' +
            (image.filename === selected ? ' hand-choice-active' : '')
          }
          onClick={() => onPick(image)}
        >
          {image.label}
        </button>
      ))}
    </div>
  );
}
