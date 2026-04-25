# spotlist

A lightweight Python CLI that reads a structured `.spotlist` file and creates a Spotify playlist in your account — with no client secret, no third-party libraries beyond `requests`, and no token ever written to disk.

---

## How it works (PKCE in plain English)

Spotify's PKCE flow lets this tool prove it is *your* authorised app without ever knowing your Spotify password or holding a client secret:

1. The tool generates a random one-time secret (the *code verifier*).
2. It sends a cryptographic hash of that secret (the *code challenge*) to Spotify.
3. Spotify asks you to log in in your browser. Your password never leaves Spotify's servers.
4. Spotify returns a short-lived auth code to a local callback server on `localhost:8888`.
5. The tool exchanges the code **plus the original verifier** for an access token. Without the verifier, the code is useless to anyone who intercepts it.

The access token lives in memory only and is discarded when the process exits.

---

## Setup

### 1. Create a Spotify Developer App

1. Go to <https://developer.spotify.com/dashboard> and log in.
2. Click **Create app**.
3. Fill in any name and description.
4. Set **Redirect URI** to exactly: `http://127.0.0.1:8888/callback`
5. Save. Copy the **Client ID** from the app overview page.

### 2. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your Client ID:

```
SPOTIFY_CLIENT_ID=abc123youractualclientid
```

That's the only value you need. There is no client secret.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Python 3.10+ required.

---

## Usage

```
python spotlist.py <playlist_file> [options]

Options:
  --dry-run       Resolve track URIs and print them without creating a playlist
  --strict        Abort if any track search returns no results (default: warn and skip)
  --segment-log   Print a per-segment summary after playlist creation
```

### Example

```bash
python spotlist.py example.spotlist --dry-run
python spotlist.py example.spotlist --segment-log
```

---

## Playlist file format

Files use the `.spotlist` extension (plain text, any editor):

```
[playlist]
name = Kids Party 2025
description = Party playlist — all segments

[segment: Pre-Party Rock]
duration_target = 60min

- Johnny B. Goode | Chuck Berry
- Rock Around the Clock | Bill Haley & His Comets

[segment: Wind Down]
duration_target = 20min

- What a Wonderful World | Louis Armstrong
```

- Segments are logical groupings (informational only — Spotify has no native concept of segments).
- `duration_target` is for your reference and is not enforced.
- Each track line: `- Song Title | Artist Name`

---

## What this tool never does

- Stores tokens or credentials on disk
- Requires a client secret
- Makes calls to any service other than `accounts.spotify.com` and `api.spotify.com`
- Logs or prints your access token
- Edits or deletes existing playlists

---

## NEVER COMMIT `.env`

> **Warning:** Your `.env` file contains your Spotify Client ID and must never be committed to version control.
>
> It is listed in `.gitignore` for this reason. Before pushing to any remote, run `git status` and confirm `.env` does not appear in the staged files.
>
> If you accidentally commit it, rotate your Client ID immediately at <https://developer.spotify.com/dashboard>.

---

## Project structure

```
spotlist/
├── spotlist.py      # CLI entrypoint
├── auth.py          # PKCE OAuth flow
├── spotify.py       # Spotify Web API calls
├── playlist.py      # .spotlist file parser
├── .env.example     # credential template
├── .gitignore
├── requirements.txt
└── README.md
```
