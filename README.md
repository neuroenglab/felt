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

### Deploy behind reverse proxy under `/felt/`

When serving FELT at `https://server/felt/`, you must configure both build-time and runtime paths.

1. Build image with frontend base path:

```bash
docker build \
  --build-arg VITE_BASE_PATH=/felt/ \
  -t felt:subpath .
```

2. Run container with FastAPI root path:

```bash
docker run -d --rm \
  -p 5000:5000 \
  -e ROOT_PATH=/felt \
  -v $(pwd)/logging:/app/logs \
  --name felt felt:subpath
```

3. Nginx location must preserve forwarded headers and strip the prefix:

```nginx
location /felt/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Prefix /felt;
}
```

If you use `docker compose`, set:

```bash
VITE_BASE_PATH=/felt/ ROOT_PATH=/felt docker compose up --build -d
```

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

## Console link

FELT can link to the calibration console, so the tablet names the trial it
scores, accepts a drawing only while the console scores that trial, and sends
the painting to the console as a request.

One address configures the link:

```bash
uv run main.py --log-dir ./logs --console-url http://127.0.0.1:8000
```

* `--console-url <address>` names the console, for example
  `http://127.0.0.1:8000`.
* `CONSOLE_URL` is the same setting as an environment variable, for the Docker
  container. The option wins over the variable.
* Without either, FELT is not linked and works exactly as before.

Two routes serve the link:

* `GET /api/trial` answers `{"linked": false}` when no address is set.
  Otherwise it answers `linked`, `reachable`, `state`, `sentence`,
  `subject_code`, `sequence_id`, `trial_id`, `pass_index`, `trial_saved`,
  `felt_answered`, `hand`, `manual` (no sequence runs) and `can_draw`. The
  service reads `GET /calibration/sequence/status` of the console, with a
  timeout of two seconds and a cache of one second, so many tablets do not
  flood the console.
* `POST /api/save-feedback` takes the two optional fields `trial`
  (`subject_code`, `sequence_id`, `trial_id`) and `felt` beside the fields it
  always took. It writes the file as before, with the two fields and one
  export time, and posts the same object to
  `POST /calibration/sequence/felt` of the console. Its answer carries
  `console`: `accepted`, `regions`, `problem` and `reason`. A refusal of the
  console, and an unreachable console, come back as `accepted` false with the
  reason.

The page reads `GET /api/trial` once per second and shows a trial banner at the
top of the mark page:

* `SCORING`, before Save: "Subject S01 · trial tr_0007 · pass 1 · draw and
  send" in green. The subject draws and sends.
* `STIMULATING`: "Wait, stimulating" in blue.
* The other states of a running sequence: "No trial to score" in grey.
* `IDLE`, no sequence: "No sequence, manual mode" in grey. The page then works
  as the unlinked page, with its prompt for the log identifier and its export
  to the file.
* No answer from the console: "Console not reachable" in red.
* After an answer of the current trial: "Answered, you can send again".

While a sequence runs, the drawing surface is locked outside `SCORING` and
after Save, and the lock names the reason. The page then offers the two hand
images only, Left hand and Right hand. They live in `hands/` of the repository
and the service serves them under `/hands/`, so a tablet needs no upload; the
uploaded images stay for the unlinked page and the manual mode. The hand of the
console is preselected at the start of a sequence, and the banner adds
" · the image is the other hand" in red when the chosen image is the other
side. The log identifier is the subject code, with no prompt. The button reads
"Send for trial tr_0007", and a second button, "Nothing felt", sends an empty
painting with `felt` false. The toast reads
"Sent for trial tr_0007: d2_distal, d2_middle" in green, or the refusal of the
console in red. The painting stays on the screen and clears when the trial
changes.

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

*Do not forget to change `<version>` (e.g. 0.0.5)*

```sh
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --build-arg VITE_BASE_PATH=/felt/ \
  -t ghcr.io/neuroenglab/felt:v<version> \
  --push .
```

1. Build image:
`docker compose build --no-cache`

2. Tag image:
`docker tag felt-app ghcr.io/neuroenglab/felt:v<version>`

3. Push image:
`docker push ghcr.io/neuroenglab/felt:v<version>`
