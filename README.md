# Counter Strike 2 Tournament Discord bot

This bot is intended to be an assistant for semi-automate a Counter Strike 2 tournament using a Discord bot. 

## Features

The features of the bot are:

- Team management: Create and remove teams and players.
- Major-like tournament automatically created.
  - [Swiss-system elimination stage](https://en.wikipedia.org/wiki/Swiss-system_tournament).
  - Elimination stage (quarterfinal, Semifinal, Third-place and Final).
- Auto creation of games.
- Map pick and bans system.
- Creation of all necessary Discord roles, text and voice channels.
- Summaries for tournament and games.

## Missing features

This bot is in a very early stage, so keep in mind that bugs and missing features exists:

- [ ] Adding a `league-system` instead of `swiss-system` before elimination stage. 
- [ ] Adding more teams, now only 16 teams can be added.
- [ ] Add RCON commands for automatically starting matches using [MatchZy match_setup](https://shobhit-pathak.github.io/MatchZy/match_setup/).
- [ ] Receive [MatchZy Events & Forwards](https://shobhit-pathak.github.io/MatchZy/events_and_forwards/) for automatically set map and games winners.
- [ ] Auto host games in [dathost](https://dathost.net/) using their API.
- [ ] Timer for getting game information in [dathost](https://dathost.net/) server until map is over.
- [ ] Permit team and players names with space

## How to use

### Create a Discord bot and retrieve the token

Follow [https://discord.com/developers/docs/quick-start/getting-started](https://discord.com/developers/docs/quick-start/getting-started) for creating a Discord application and retrieving the token. Once you have the token, create an `.env` file like [sample](./.env.sample) provided and change the mock token for yours.

### Deploying using docker compose

Deployment using `docker compose` is easy, just run:

```bash
docker compose up -d
```

On the repo root folder.

### Add the bot to your Guild/Server

From your developer console, create a link for your application and add the bot to your server.

### Use the bot

For using the bot, you have to do:

1. In any Text Channel, write `!start` command. It will create all categories and channels needed for starting. Now the `Admin` channel is created, so please use the global management commands from there.
2. From `Admin` channel, create the teams. You can create a test example using `!mock_teams`, but for doing it manually, you can, for example:
   1. `!create_team Iberian_Soul`
   2. `!add_player Iberian_Soul alex 76561198000984547 captain`
   3. `!add_player Iberian_Soul Stadod0 76561198047402862 player`
   4. `!add_player Iberian_Soul Dav1g 76561197998197366 player`
   5. `!add_player Iberian_Soul Mopoz 76561198417348056 player`
   6. `!add_player Iberian_Soul SausoL 76561197991593267 player`
   7. `!add_player Iberian_Soul DeLonge 76561198028497770 coach`
3. Once you have the 16 teams created, add to each user in discord their role, which are in the example above `Iberian_Soul_captain`, `Iberian_Soul_player`. `Iberian_Soul_coach`
4. Execute from `Admin` channel `!all_teams_created`. The channels on `Swiss stage round 1` will be randomly created the games. For each game, an admin channel and a public channel are created. On the game-admin channel only the captains can write and is used for picks & bans, but you can also use it for internal game communication between teams and org. The idea is to have also public-game-channel to show information about the match.
5. On each game, the captain of each team have to send vetoes and picks. Send `!veto dust2` for vetoing dust2 or `!pick inferno` for picking inferno. Once all vetoes and picks are selected, decider will be automatically selected.
6. Once all games are finished, automatically new games will be created, respecting the current streak of each team.
7. Once the swiss-stage is finished, quarterfinal will be created. The same for the rest of elimination stage.

