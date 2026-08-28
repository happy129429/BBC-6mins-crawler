# BBC-6mins-crawler

Languages: [English](README.md) / [简体中文](README-zh.md)

## Introduction

A set of Python scripts for batch-crawling episode metadata, transcripts and media files of BBC Learning English's 6 Minute English from the official BBC website, for personal offline learning.

The workflow consists of two relatively independent steps:

1. **JSON generator** (`scripts/json_generator.py`): scrapes episode metadata (title, link, date, description) from the programme index page and writes it to a JSON file using **incremental merging** — download-progress fields such as `media_download_url` and `local_media_path` in existing records are **never overwritten**, so it is safe to run repeatedly.
2. **Downloader** (`scripts/downloader.py`): reads the JSON, downloads the transcript (cleaned and saved as txt) and the media file for each episode from oldest to newest, and writes results back to the JSON. Completed episodes are skipped automatically; interrupted runs can be resumed.

## Project Structure

```
BBC-6mins-crawler/
├── .gitignore              # Ignore bytecode caches, logs, download outputs, etc.
├── LICENSE                 # GPL-3.0
├── README.md               # English readme (this file)
├── README-zh.md            # Chinese readme
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # Dev/test dependencies
├── pytest.ini              # Test configuration
├── scripts/
│   ├── config.py           # Central configuration (paths, switches, timeouts, retries)
│   ├── utils.py            # Shared utilities (filename sanitising, transcript cleaning,
│   │                       #   media-link extraction, retry, logging)
│   ├── json_generator.py   # Metadata scraping + incremental merging
│   └── downloader.py       # Transcript/media downloader
└── tests/                  # Offline unit tests (pytest + local HTML fixtures)
```

## Requirements

- Python 3.8+ (developed and tested on Python 3.12)
- Runtime dependencies: `requests`, `beautifulsoup4`
- Optional external tools:
  - **ffmpeg**: needed to extract audio from video; the feature degrades gracefully when missing
  - **yt-dlp**: needed for pages that offer no direct download link but expose an mpd streaming manifest; such pages are logged and skipped when missing

## Installation

```bash
pip install -r requirements.txt
```

For development and testing:

```bash
pip install -r requirements-dev.txt
```

## Usage

From the project root, run the two scripts in order (the JSON file and logs are created in the working directory):

```bash
# Step 1: scrape / incrementally update metadata (safe to re-run; existing progress is kept)
python3 scripts/json_generator.py

# Step 2: download transcripts and media (completed episodes are skipped)
python3 scripts/downloader.py
```

On Windows, replace `python3` with `python`. Console output is in Simplified Chinese by default.

**Save directory**: defaults to `downloads/` under the current working directory. Two ways to customise:

```bash
# Option 1: environment variable (recommended, no code changes)
# Linux / macOS
BBC6_SAVE_DIR=/home/me/BBC6minute python3 scripts/downloader.py
# Windows (PowerShell)
$env:BBC6_SAVE_DIR='D:\BBC6minute'; python scripts\downloader.py

# Option 2: edit the defaults in scripts/config.py
```

**Console language**: output defaults to Simplified Chinese. Two ways to switch to English:

```bash
# Option 1: environment variable (per run only)
# Linux / macOS
BBC6_LANG=en python3 scripts/downloader.py
# Windows (PowerShell)
$env:BBC6_LANG='en'; python scripts\downloader.py

# Option 2: set OUTPUT_LANGUAGE = "en" in scripts/config.py (persistent)
```

Other tunables (max episodes per run `MAX_ITEMS`, audio extraction from video, whether to keep the original video, request timeout and retry counts, etc.) are centralised in `scripts/config.py`.

## Media Download Strategy

For each episode the downloader tries, in order, stopping at the first success:

1. Direct links in the page's download area, detected and saved by their real URL extension (audio `.mp3/.wav/.m4a/.aac`, video `.mp4`, etc.);
2. Direct links in the page's `<audio>/<video>` tags and `data-media` attributes;
3. If no direct link exists, scan the page for an **mpd streaming manifest**, download it with `yt-dlp`, then extract audio with `ffmpeg` (mirrors the manual workflow: F12 → find the mpd → yt-dlp → ffmpeg).

Video files are converted to mp3 audio by default and the original video is deleted (both configurable in `config.py`).

## Logging

While printing to the console, both scripts also write logs to `json_generator.log` and `downloader.log` in the working directory, which makes post-mortem analysis easier (VPN drops, individual page parse failures, etc.).

## Running Tests

```bash
python3 -m pytest
```

All tests run offline (against local HTML fixtures in `tests/fixtures/`); no access to BBC servers is required.

## Known Limitations

- `json_generator` only scrapes the episodes listed on the index page; it does not paginate;
- Layout changes on the BBC site may break parsing; in that case update the selectors in `scripts/utils.py` (the fixtures serve as regression samples);
- The mpd route requires `yt-dlp` and video-to-audio extraction requires `ffmpeg`; missing tools are reported in the log and the affected steps are skipped;
- No VPN/proxy configuration is bundled; solve network access yourself.

## Roadmap

- [x] Code and naming clean-up (config/utils split, no duplicate imports)
- [x] Incremental JSON updates that never overwrite existing download URLs
- [x] File logging
- [x] Support .wav/.m4a and other formats (saved with their real extensions)
- [x] mpd pages via yt-dlp + ffmpeg
- [x] Cross-platform paths (Linux/Windows/macOS)
- [x] Offline unit tests
- [x] Configurable console output language (English)
- [ ] Fetch episodes via RSS/podcast subscription (an alternative to crawling)
- [ ] Paginate through the full episode archive
- [ ] Rate limiting and resumable downloads

## AI Assistance Statement

The bulk of this project's code was generated with AI assistance (initial version: DeepSeek LLM; August 2026 refactor: GLM). The human author conceived the project and performed code review and debugging with AI assistance.

## Open Source Statement

The source code of this project is licensed under the GNU General Public License v3.0. BBC content, including audio and transcripts, is not part of this project and thus not covered by this license.

## Copyright

This project is not affiliated with or endorsed by the BBC. All BBC content remains the property of its respective rights holders. If you are a rights holder and have concerns about this project or its distribution of content, please contact me and I will promptly remove or modify the relevant material.
