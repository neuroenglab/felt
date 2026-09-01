# nel-feedback-ui

Neuroengineering feedback UI: body part selector and sensation locator React components.

## Install

The package is published publicly on the npm registry. No authentication or token is required:

```bash
npm install @neuroenglab/nel-feedback-ui
```

## Build the package

Clone this repo and install dependencies:

```bash
npm install
```

Build the library into `dist/`:

```bash
npm run build
```

This produces:

- `dist/nel-feedback-ui.es.js` (ESM)
- `dist/nel-feedback-ui.umd.js` (UMD)
- `dist/*.d.ts` (TypeScript declarations)

## Publish

Publishing is only needed by maintainers. The package targets the public npm registry as a public scoped package (`publishConfig.access` is set to `public`).

1. Log in to npm (one time):

   ```bash
   npm login
   ```

2. Bump the `version` in `package.json`, then publish (the build runs automatically via `prepublishOnly`):

   ```bash
   npm publish
   ```

## Exports

- **Components:** `BodyPartSelector`, `FeedbackLocator`
- **Types:** `SelectionResult`, `SensationLocation`, `FeedbackLocatorProps`, `ChosenPointsDict`, `ImageSize`, `SegmentSizePx`

```tsx
import {
  BodyPartSelector,
  FeedbackLocator,
  type SelectionResult,
  type SensationLocation,
  type FeedbackLocatorProps,
  type ChosenPointsDict,
  type ImageSize,
  type SegmentSizePx,
} from '@neuroenglab/nel-feedback-ui';;

// BodyPartSelector: pass asset URLs, get selection (path, bodyPart, side)
// FeedbackLocator: pass image URL and optional SensationLocation, get updates via onUpdate
```

## Component API

### ***FeedbackLocator***

A grid-based overlay component that allows users to "paint" sensation areas over a body part image. It features a brush-based selection tool and automatic transparency masking.

**Props**

| Prop | Type | Description |
| :--- | :--- | :--- |
| `imageSrc` | `string` | **Required.** The URL or path of the image to display. |
| `onUpdate` | `(location: SensationLocation) => void` | **Required.** Callback triggered whenever the selection or coarseness changes. |
| `feedbackLocation` | `SensationLocation` | Optional. Current state to initialize or control the component. |
| `coarseness` | `number` | Optional. Default grid density (0-100). Defaults to `90`. |

**SensationLocation Object**

```typescript
{
  image_path: string;        // Path to the image used
  image_size: { w: number, h: number };      // Rendered dimensions of the image
  segment_size_px: { w: number, h: number }; // Size of a single grid cell in pixels
  coarsenessPercent: number; // The grid density used
  chosenPoints: {            // Parallel arrays of selected cell coordinates
    row: number[];
    col: number[];
  };
}
```

### ***BodyPartSelector***

A dropdown and radio button interface to navigate through available body part assets based on a specific naming convention.

#### Props

| Prop          | Type                                     | Description                                                                 |
|---------------|------------------------------------------|-----------------------------------------------------------------------------|
| assets        | `Record<string, string>`                 | Required. Map of keys to image URLs. Keys must follow the naming convention below. |
| onSelect      | `(selection: SelectionResult) => void`   | Required. Callback when a part or side is picked.                            |
| selectedPath  | `string`                                 | Optional. The URL of the currently selected asset for controlled state.      |

#### SelectionResult Object

```ts
{
  path: string;        // The URL of the specific asset
  bodyPart: string;    // The category (e.g., 'hand', 'arm')
  side: string | null; // 'left', 'right', or null for center/default
}
```

## Asset Naming Convention

The `BodyPartSelector` parses the keys of your `assets` object to build the UI. Keys should be formatted using hyphens as delimiters:

`part-side-Nice_Name.svg`

* part: The internal ID for the body area (e.g., hand, leg).
* side: The lateral identifier. Use an empty string for "Center" or a specific side (e.g., left, right).
* Nice_Name: The human-readable label. Underscores are automatically converted to spaces.

**Example Keys:**
* hand-left-Left_Hand: Becomes Part: hand, Side: left, Label: Left Hand.
* torso--Chest_Area: Becomes Part: torso, Side: , Label: Chest Area.


## Peer dependencies

- "react": "^18.0.0 || ^19.0.0",
- "react-dom": "^18.0.0 || ^19.0.0"
