# Featherstorm

A League of Legends companion CLI tool.

Features a (hopefully) simple config system for toggling certain behaviors or features.

## Modules

### Companion
`featherstorm companion` will run the tool in 'companion' mode alongside your live match.

Currently it will:
- Enable Discord Rich Presence (see below)
- Enable Razer Chroma lighting
- Enable Govee light controls
- Print notable game events to the console

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
