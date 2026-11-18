/**
 * The two hand images of the linked page. They travel with the repository and
 * the service serves them from `/hands/`, so the tablet needs no upload.
 */
export type HandImage = {
  side: 'left' | 'right';
  label: string;
  filename: string;
  url: string;
};

export const HAND_IMAGES: HandImage[] = [
  {
    side: 'left',
    label: 'Left hand',
    filename: 'hand-left-Left_Hand.svg',
    url: 'hands/hand-left-Left_Hand.svg',
  },
  {
    side: 'right',
    label: 'Right hand',
    filename: 'hand-right-Right_Hand.svg',
    url: 'hands/hand-right-Right_Hand.svg',
  },
];

/** The image of the hand the console names, if it names one. */
export function handImage(hand: string | null | undefined): HandImage | null {
  if (!hand) return null;
  const side = hand.toLowerCase();
  return HAND_IMAGES.find((image) => image.side === side) ?? null;
}
