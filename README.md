# FELT: Perception Feedback Tool

Interactive web app for marking perceived sensations on body-part SVGs and exporting structured logs.

## Install

### Prerequisites

#### 1. Authentication for GitHub Container Registry (ghcr.io)

To pull Docker images from this organization, you must authenticate using a GitHub Personal Access Token (PAT).

### 1. Generate a Personal Access Token (PAT)
1. Go to **GitHub Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Select the **`read:packages`** scope (and `write:packages` if you need to push).
4. **Copy the token; you will not be able to see it again.**

### 2. Login via Terminal
Run the following command in your terminal, replacing the placeholders with your details:

```bash
export CR_PAT=YOUR_TOKEN_HERE
echo $CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```
Once you see Login Succeeded, you can pull images using: docker pull ghcr.io/ORGANIZATION_NAME/IMAGE_NAME:TAG

### Run with Docker (recommended)

1. Pull image:

```bash
docker pull ghcr.io/neuroenglab/felt:v<version>
```

2. Start container:
```bash
docker run -d --rm -p 11055:5000 -v $(pwd)/logging:/app/logs --name felt ghcr.io/neuroenglab/felt:v<version>
```

2. Open the app in your browser:

```text
http://localhost:11055
```

3. Logs:

- Saved JSON logs are written into the `logging/` directory on the host.

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

## Releasing

### Github

Tag commit on the master branch:
`git tag -a v<version> -m <release_message>`

Push to github:
`git push origin v<version>`

### Docker

Build:
`docker compose build --no-cache`

Tag:
`docker tag felt-app ghcr.io/neuroenglab/felt:v<version>`

Push:
`docker push ghcr.io/neuroenglab/felt:v<version>`

