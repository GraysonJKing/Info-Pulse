# Info Pulse

Info Pulse is a Python pipeline that turns raw news feeds into personalised morning market briefs.
It fetches Google News RSS stories, triages for market relevance, runs deeper analysis, updates persistent story memory, generates per-user markdown briefs, and optionally delivers them to Microsoft Teams webhooks.

## What the pipeline does

The pipeline runs in `main.py` and executes these steps:

1. **Cleanup** (`steps/cleanup.py`)
  - Clears ephemeral output folders/files from the previous run.
2. **Fetch + Dedup** (`steps/fetch.py`)
  - Pulls 8 Google News RSS feeds.
  - Deduplicates by GUID and filters out old stories (default: older than 24h).
  - Writes article chunks for parallel triage.
3. **Triage** (`agents/triage.py`)
  - Runs 8 parallel triage agents.
  - Scores stories for market impact, deduplicates, then clusters by topic.
4. **Analysis** (`agents/analysis.py`)
  - Runs one analyst agent per notable story with web tools enabled.
  - Produces structured JSON analysis per story.
5. **Memory curation** (`agents/memory.py`)
  - Updates ongoing story memory and enforces safety rules (staleness, caps).
6. **Personalisation** (`agents/personalise.py`)
  - Runs one personaliser agent per user.
  - Writes markdown briefs to `data/personalised/`.
7. **Delivery** (`steps/deliver.py`)
  - Converts markdown to Teams-compatible HTML.
  - Sends chunked payloads to configured Teams webhooks.

## Project structure

```text
.
├─ main.py
├─ config.py
├─ requirements.txt
├─ .env.example
├─ agents/
├─ steps/
├─ utils/
├─ prompts/
└─ data/
   ├─ users_example.json
   ├─ users.json              # ignored by git, create locally
   ├─ memory.md
   ├─ feeds/
   ├─ triage/
   ├─ analysis/
   └─ personalised/
```

## Requirements

- Python 3.11+
- Anthropic API key
- Internet access (RSS + analysis web tools)

## Environment setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Create `.env` from `.env.example`:

```env
ANTHROPIC_API_KEY=your_key_here
grayson_teams_webhook=https://your-teams-webhook-url
```

1. Create `data/users.json` (use `data/users_example.json` as a starting point).
   - Keep `username` values in sync with env variable names.
   - Delivery reads Teams webhook from `{username}_teams_webhook` (and also supports `{USERNAME}_TEAMS_WEBHOOK`).

## Run locally

From the project root:

```bash
python main.py
```

## Output artifacts

Generated each run (ephemeral):

- `data/articles.json`
- `data/feeds/chunk_*.json`
- `data/triage/shard_*.json`
- `data/todays_notable.json`
- `data/analysis/*.json`
- `data/personalised/*.md`

Persistent data:

- `data/memory.md`
- `data/users.json`

## Docker

Build image:

```bash
docker build -t info-pulse .
```

Start container (keeps running; useful for exec/debug):

```bash
docker run --name info-pulse --env-file .env info-pulse
```

Run the pipeline inside the running container:

```bash
docker exec -it info-pulse python -u main.py
```

Or run once directly by overriding command:

```bash
docker run --rm --env-file .env info-pulse python -u main.py
```

