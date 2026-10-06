# Featherstorm

A League of Legends companion CLI tool.

> [!WARNING]
> This is a personal project and is not configured to be generally installable and runnable without making changes. If you'd still like to try, be sure to read the "Usage" section carefully.

## Modules

### Companion
`featherstorm companion` will run the tool in 'companion' mode alongside your live match.

Currently it will:
- Enable Discord Rich Presence (see below)
- Enable Razer Chroma lighting (if installed and enabled)
- Enable Govee light controls (if installed and enabled)
- Print notable game events to the console

For lighting to work, you need to install Featherstorm with the optional `[lighting]` group.

#### Discord Rich Presence
<img width="306" height="141" alt="image" src="https://github.com/user-attachments/assets/80c9b0be-a195-4708-97c8-85edc2441872" />

Changes your current activity on Discord to show your currently active match, including the following:
- Queue type (ranked solo, practice, ARAM, etc.)
- Champion name and skin
- Enemy lane opponent champion
- Lane/role
- KDA and CS
- Game duration

### Game Highlights
The `featherstorm highlights capture` command will automatically parse your last match, open the replay, then capture highlight recordings. Optionally, you can provide a match ID.

Once capture is complete, it will automatically convert the replay from `webm` to `mp4`, which helps greatly reduce the file size (we record losslessly, so the webm files explode in size).

### League Client API
The `featherstorm lcu` module contains commands for interacting with the League of Legends client.

Currently:
- Fetch logged in summoner info
- Fetch match history
- Fetch last match info
- Currently locked or hovered champion in champ select
- Current lobby info

### Riot API
The `featherstorm riot` module contains commands that interact with the Riot Games web API.

Allows you to fetch:
- Match history
- Specific matches by ID
- PUUIDs
- Match timelines
- Ranked leaderboards
- Live match information

### Replay API
The `featherstorm replay` module provides commands that allow you to control and manage match replays.

Currently:
- Downloading replay files
- Opening replays
- Play/pause
- Record/end recording
- Hide UI
- Follow a specific player champion
- Seeking forward/back
- Changing playback speed

### Data Dragon API
The `featherstorm dragon` module contains commands for interacting with the Riot Data Dragon API.

Allows you to fetch:
- Item info by ID
- Champion info by ID
- Champion splash art by champion name

## Usage

### Installation
First off, you need [uv](https://docs.astral.sh/uv/getting-started/installation/). Technically this isn't required, but who uses `pip` these days anyways?

Once you have [uv](https://docs.astral.sh/uv/getting-started/installation/), you can install Featherstorm with the following command:
```
uv tool install "featherstorm @ git+https://github.com/Ghostopheles/featherstorm"
```
or, you can clone the repository locally, and use `uv run` to run without installing globally.

### Configuration
You can set configuration values using `featherstorm cfg set`. For example, you can change your summoner name with `featherstorm cfg set companion default_player_name MySuperCoolSummonerName`.

Using this system, you'll want to change the following default config values:
- `meta.cache_dir`: Point this to the folder that Featherstorm should use for caching data.
- `lcu.client_install_path`: Point this to your League of Legends installation, required for League Client API functionality.
- `highlights.export_path`: Export path for auto-captured highlights.
- `discord.app_id`: Change this to your own Discord application ID. Used for rich presence.
- `companion.default_player_name`: Your summoner name.
- `companion.default_player_tagline`: Your summoner tagline (the thing after the #).

You can view your current configuration with `featherstorm cfg view`.

### Docker
If you decide to use the match crawler (I don't recommend it), you'll need to use [Docker](https://docs.docker.com/engine/install/) and run `docker compose up` in the repo to set up the match database container.

> [!DANGER]
> The default container configuration exposes the match database on **all** network interfaces and has horrendously insecure login credentials. Just so you're aware.
>
> It also has a hardcoded data volume path. Probably change that if you care.

## AI Usage
Parts of this project were written by Claude Code, but *most* of the code remains human-written.
