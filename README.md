# FELT: Perception Feedback Tool

A marking page for tablets: the subject paints where a sensation is felt on a
body-part SVG, and the service writes structured logs and, when linked, sends
the painting to a calibration console.

FELT is a Python package. A pipeline starts it with one function call, an
operator with one command, and the marking page ships inside the package, so
nobody needs Node or a clone of this repository to run it.

## Install

With `uv`, as a tool on PATH (the `felt` command):

```
uv tool install git+https://github.com/neuroenglab/MobileFeedback@v0.1.0
```

As a dependency of a Python project:

```
uv add git+https://github.com/neuroenglab/MobileFeedback@v0.1.0
pip install git+https://github.com/neuroenglab/MobileFeedback@v0.1.0
```

Python 3.12 or newer. Drop the `@v0.1.0` for the latest commit, or pin a
commit instead of a tag.

## Start from Python

```python
import felt

server = felt.start(tailscale=True, console_url="http://127.0.0.1:8765")
print(server.url)                     # http://100.x.y.z:5000, for the tablet
server.wait_for_marking_page()        # until a tablet opens the page
...
server.stop()
```

`felt.start(...)` serves on a background thread of the calling process and
returns once the port answers. It takes:

| Argument | Default | Meaning |
|---|---|---|
| `host` | `127.0.0.1` | The interface to bind. `0.0.0.0` for every network of the PC. |
| `port` | `5000` | The TCP port. |
| `tailscale` | `False` | Bind this PC's Tailscale address instead of `host`. |
| `log_dir` | `./logs` | Where the feedback logs are written. |
| `images_dir` | `./uploads` | Where uploaded body-part SVGs live. |
| `console_url` | none | The calibration console to link, for example `http://127.0.0.1:8765`. |
| `root_path` | none | The prefix a reverse proxy strips, for example `/felt`. |

It raises `felt.TailscaleError` when `tailscale=True` and Tailscale is not
installed, not running or not logged in. The message says how to install it
and how to start without it (`host="0.0.0.0"`). It raises `felt.FeltError`
when the port is taken.

The returned `FeltServer` has `url`, `running`, `marking_page_open()`,
`marking_clients()`, `wait_for_marking_page(timeout_s)` and `stop()`, and it
works as a context manager:

```python
with felt.FeltServer(felt.Settings(port=5000, log_dir="runs/S01/felt")) as server:
    ...
```

`felt.serve(...)` takes the same arguments and serves on the calling thread
until Ctrl+C.

A process that did not start FELT asks a running one with `felt.FeltClient`:

```python
tablet = felt.FeltClient("http://100.x.y.z:5000")
tablet.reachable()
tablet.wait_for_marking_page(timeout_s=120)
tablet.trial()                        # what the page shows about the console link
```

## Start from a terminal

```
felt --tailscale --log-dir ./logs --console-url http://127.0.0.1:8765
```

`felt --help` lists the options; they are the arguments of `felt.start`, plus
`--build` (rebuild the page from a clone), `--reload` (restart on source
changes) and `--version`. The environment variables `FELT_HOST`, `FELT_PORT`,
`LOGS_DIR`, `IMAGES_DIR`, `CONSOLE_URL` and `ROOT_PATH` are the defaults of
the same settings; an option wins over its variable.

Without Tailscale, bind another interface and give the tablet the address of
the PC on that network:

```
felt --host 0.0.0.0 --log-dir ./logs
```

## Run with Docker

```
docker run -d --rm -p 11055:5000 -v "${PWD}/logs:/app/logs" --name felt ghcr.io/neuroenglab/felt:v<version>
```

The image is built from this repository with `docker compose up --build`.
`CONSOLE_URL` and `ROOT_PATH` are read from the environment. To pull the
image, log in to `ghcr.io` with a GitHub token that has `read:packages` (see
Releasing).

### Behind a reverse proxy under `/felt/`

The page is built for the root by default. For a prefix, build the image with
the prefix and run it with the matching root path:

```
VITE_BASE_PATH=/felt/ ROOT_PATH=/felt docker compose up --build -d
```

Nginx must preserve the forwarded headers and strip the prefix:

```nginx
location /felt/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Prefix /felt;
}
```

## Develop

From a clone, with Node 22 or newer:

```
uv sync
cd frontend && npm install && cd ..
uv run felt --build --reload
```

`npm run build` writes the page to `src/felt/static`, where the package serves
it. `npm run dev` in `frontend/` serves the page with hot reload and proxies
`/api` to a `felt` on port 5000. `uv run pytest` runs the tests.

## Console link

FELT can link to the calibration console, so the tablet names the trial it
scores, accepts a drawing only while the console scores that trial, and sends
the painting to the console as a request.

One address configures the link:

```bash
felt --log-dir ./logs --console-url http://127.0.0.1:8000
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
  `felt_answered`, `hand`, `manual` (no sequence runs), `can_draw` and
  `purpose` (`target` while the subject paints the target of the run,
  `sensation` while the console scores a trial, null otherwise) and `target`
  (the painting the console accepted as the target of the run,
  `{"feedbackLocation": ...}`, or null when the console sends none, so a page
  that reloads mid-run paints its underlay again). The service reads
  `GET /calibration/sequence/status` of the console, with a
  timeout of two seconds and a cache of one second, so many tablets do not
  flood the console.
* `POST /api/save-feedback` takes the optional fields `trial`
  (`subject_code`, `sequence_id`, `trial_id`), `felt`, `pain` (a boolean) and
  `intensity` (a number from 0 to 10, or null) beside the fields it
  always took. It writes the file as before, with the fields it was given and
  one export time; a field left out, or null, is left out of the file. It
  posts the same object to `POST /calibration/sequence/felt` of the console.
  Its answer carries
  `console`: `accepted`, `regions`, `problem` and `reason`. A refusal of the
  console, and an unreachable console, come back as `accepted` false with the
  reason.

The page reads `GET /api/trial` once per second and shows a trial banner at the
top of the mark page:

* `SCORING`, before Save: "Subject S01 · trial tr_0007 · pass 1 · draw and
  send" in green. The subject draws and sends.
* `TARGET`, before Save: "Subject S01 · paint the target · Paint the target
  reach, then send" in green, with the sentence of the console. The panel
  reads "2. Paint the target", the brush paints green instead of the red of a
  sensation, the button reads "Send the target", and the page offers no
  Nothing felt. The toast reads "Sent the target: d2_distal".
* `STIMULATING`: "Wait, stimulating" in blue.
* The other states of a running sequence: "No trial to score" in grey.
* `IDLE`, no sequence: "No sequence, manual mode" in grey. The page then works
  as the unlinked page, with its prompt for the log identifier and its export
  to the file.
* No answer from the console: "Console not reachable" in red.
* After an answer of the current trial: "Answered, you can send again".

While a sequence runs, the drawing surface is locked outside `SCORING` and
`TARGET`, and after Save, and the lock names the reason. The page then offers
the two hand images only, Left hand and Right hand. They ship inside the
package and the service serves them under `/hands/`, so a tablet needs
no upload; the uploaded images stay for the unlinked page and the manual mode.
The hand of the console is preselected at the start of a sequence, and the
banner adds " · the image is the other hand" in red when the chosen image is
the other side. The log identifier is the subject code, with no prompt. The
button reads "Send for trial tr_0007", and a second button, "Nothing felt",
sends an empty painting with `felt` false. The toast reads
"Sent for trial tr_0007: d2_distal, d2_middle" in green, or the refusal of the
console in red. The painting stays on the screen and clears when the trial
changes.

Once the console accepts the target, the target stays as a pale green layer
under the painting of every following trial, so the subject sees the reach they
described. The layer is read-only: it takes no brush, and it leaves the sent
painting untouched. A target sent again replaces it, and the end of the
sequence, manual mode or a new sequence drops it. A page that reloads mid-run
has no target of its own and takes the one `GET /api/trial` reports in
`target`; a console that reports none leaves the page without a layer until the
next target is sent.

While the console scores a trial, the page asks for two more answers beside the
painting, above the drawing surface:

* **Pain**, a toggle, off at the start of every trial.
* **Intensity**, the steps 0 to 10, "not set" at the start of every trial. A
  second press on the chosen step sets it back to not set.

Both travel in the sent object as `pain` and `intensity`, for example
`{"felt": true, "pain": true, "intensity": 7, ...}`. Nothing felt sends the
pain as it stands and `"intensity": null`. The target carries neither field.

## Releasing

### Python package

The built marking page is committed under `src/felt/static`, so a git install
carries it. A release is:

1. Bump `version` in `pyproject.toml`.
2. Build the page and commit it, from the clone:

   ```
   cd frontend && npm install && npm run build && cd ..
   git add src/felt/static pyproject.toml
   git commit -m "release v<version>"
   ```

3. Tag and push:

   ```
   git tag -a v<version> -m <release_message>
   git push origin master v<version>
   ```

`uv run pytest` before the tag. `uv build` makes the wheel and sdist under
`dist/` when a file is wanted, for example as a release asset.

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


### Marking-client presence and idle console status

The marking page renews a client lease every two seconds. `GET /api/clients`
reports whether at least one marking interface is present and the number of
clients. Loading server health or image endpoints does not register a client.
Closing a page releases its lease; disconnected pages expire after seven seconds.
MAGI uses this endpoint to distinguish the server being online from a tablet or
browser being available to mark sensations.

When calibration is IDLE, the marking page asks `/api/trial?wait=25`. FELT holds
one console status request with the last revision, so Begin wakes it immediately.
The console caps each wait at its configured long-poll limit (currently ten
seconds). A page starts its next read only after the previous read finishes;
multiple marking pages share one cached console read. After End, the page returns
to manual mode and waits for the next sequence instead of checking console status
every second. Closing all marking pages stops further reads after in-flight work
finishes. Ordinary `/api/trial` reads remain compatible with older clients.

After updating, run `felt --build` from the clone, restart FELT and refresh any
open marking pages so they use the new heartbeat and waiting behaviour.
