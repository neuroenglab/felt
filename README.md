# FELT: Perception Feedback Tool

Interactive web app for marking perceived sensations on body-part SVGs and exporting structured logs.

## How to run

### Run with Docker (recommended)

#### Requirements

* [docker](https://www.docker.com/products/docker-desktop/) installed

#### Steps

1.Pull image:

```bash
docker pull ghcr.io/neuroenglab/felt:v<version>
```

2.Start container:

Linux/WSL:
```bash
docker run -d --rm -p 11055:5000 -v $(pwd)/logging:/app/logs --name felt ghcr.io/neuroenglab/felt:v<version>
```

Windows/PowerShell

```powershell
docker run -d --rm -p 11055:5000 -v "${PWD}\logging:/app/logs" --name felt ghcr.io/neuroenglab/felt:v<version>
```

2.Open the app in your browser:

```text
http://localhost:11055
```

3.Logs:

* Saved JSON logs are written into the `logging/` directory on the host.

### Run using *uv* and *python3*

#### Steps

##### Build Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Run app

Run from application root:

```bash
uv sync
uv run main.py --log-dir ./logs
```

## Releasing

### Github

Tag commit on the master branch:
`git tag -a v<version> -m <release_message>`

Push to github:
`git push origin v<version>`

### Docker

#### Prerequisites - Authentication for GitHub Container Registry (ghcr.io)

To pull Docker images from this organization, you must authenticate using a GitHub Personal Access Token (PAT).

##### 1. Generate a Personal Access Token (PAT)

1. Go to **GitHub Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Select the **`read:packages`** scope (and `write:packages` if you need to push).
4. **Copy the token; you will not be able to see it again.**

##### 2. Login via Terminal

Run the following command in your terminal, replacing the placeholders with your details:

```bash
export CR_PAT=YOUR_TOKEN_HERE
echo $CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

#### Publishing

Following command is the preferred way, since it creates manifests for both amd and arm64 architectures.
After successful run of the command, image is already pushed to the github package repository.

*Do not forget to change `<YOUR_GH_TOKEN>` (github access token) and `<version>` (e.g. 0.0.5)*

```sh
NODE_AUTH_TOKEN=<YOUR_GH_TOKEN> docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --secret id=NODE_AUTH_TOKEN,env=NODE_AUTH_TOKEN \
  -t ghcr.io/neuroenglab/felt:v<version> \
  --push .
```

1. Build image:
`docker compose build --no-cache`

2. Tag image:
`docker tag felt-app ghcr.io/neuroenglab/felt:v<version>`

3. Push image:
`docker push ghcr.io/neuroenglab/felt:v<version>`
