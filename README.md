## Perception Feedback Tool

Interactive web app for marking perceived sensations on body-part SVGs and exporting structured logs.

### Prerequisites

- GitHub access to the `@neuroenglab/nel-feedback-ui` private package.
- A GitHub Packages token with `read:packages` scope, set as `NODE_AUTH_TOKEN`.

Example `.npmrc` (do **not** commit a real token):

```ini
@neuroenglab:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${NODE_AUTH_TOKEN}
```

Then set `NODE_AUTH_TOKEN` in your shell (or use a `.env` file for Docker Compose).

### Run with Docker (recommended)

1. Build and start:

```bash
NODE_AUTH_TOKEN=<your_personal_access_token> docker compose up --build
```

2. Open the app in your browser:

```text
http://localhost:5000
```

3. Logs:

- Saved JSON logs are written into the `logs/` directory on the host (mounted into the container).

### Local development without Docker

#### Backend

```bash
uv sync
uv run main.py --log-dir ./logs
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the Vite dev URL (usually `http://localhost:5173`) and ensure the backend is running on port `5000` for the `/api/save-feedback` endpoint.
