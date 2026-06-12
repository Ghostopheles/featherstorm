from .enum_base import LookupEnum


class Queue(LookupEnum):
    ITEM_X = 0
    Q_5V5_BLIND_PICK_GAMES = 2
    Q_5V5_RANKED_SOLO_GAMES = 4
    Q_5V5_RANKED_PREMADE_GAMES = 6
    CO_OP_VS_AI_GAMES = 7
    Q_3V3_NORMAL_GAMES = 8
    Q_3V3_RANKED_FLEX_GAMES = 9
    Q_5V5_DRAFT_PICK_GAMES = 14
    Q_5V5_DOMINION_BLIND_PICK_GAMES = 16
    Q_5V5_DOMINION_DRAFT_PICK_GAMES = 17
    DOMINION_CO_OP_VS_AI_GAMES = 25
    CO_OP_VS_AI_INTRO_BOT_GAMES = 31
    CO_OP_VS_AI_BEGINNER_BOT_GAMES = 32
    CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES = 33
    Q_3V3_RANKED_TEAM_GAMES = 41
    Q_5V5_RANKED_TEAM_GAMES = 42
    CO_OP_VS_AI_GAMES_2 = 52
    Q_5V5_TEAM_BUILDER_GAMES = 61
    Q_5V5_ARAM_GAMES = 65
    ARAM_CO_OP_VS_AI_GAMES = 67
    ONE_FOR_ALL_GAMES = 70
    Q_1V1_SNOWDOWN_SHOWDOWN_GAMES = 72
    Q_2V2_SNOWDOWN_SHOWDOWN_GAMES = 73
    Q_6V6_HEXAKILL_GAMES = 75
    ULTRA_RAPID_FIRE_GAMES = 76
    ONE_FOR_ALL_MIRROR_MODE_GAMES = 78
    CO_OP_VS_AI_ULTRA_RAPID_FIRE_GAMES = 83
    DOOM_BOTS_RANK_1_GAMES = 91
    DOOM_BOTS_RANK_2_GAMES = 92
    DOOM_BOTS_RANK_5_GAMES = 93
    ASCENSION_GAMES = 96
    Q_6V6_HEXAKILL_GAMES_2 = 98
    Q_5V5_ARAM_GAMES_2 = 100
    LEGEND_OF_THE_PORO_KING_GAMES = 300
    NEMESIS_GAMES = 310
    BLACK_MARKET_BRAWLERS_GAMES = 313
    NEXUS_SIEGE_GAMES = 315
    DEFINITELY_NOT_DOMINION_GAMES = 317
    ARURF_GAMES = 318
    ALL_RANDOM_GAMES = 325
    Q_5V5_DRAFT_PICK_GAMES_2 = 400
    Q_5V5_RANKED_DYNAMIC_GAMES = 410
    Q_5V5_RANKED_SOLO_GAMES_2 = 420
    Q_5V5_BLIND_PICK_GAMES_2 = 430
    Q_5V5_RANKED_FLEX_GAMES = 440
    Q_5V5_ARAM_GAMES_3 = 450
    Q_3V3_BLIND_PICK_GAMES = 460
    Q_3V3_RANKED_FLEX_GAMES_2 = 470
    SWIFTPLAY_GAMES = 480
    NORMAL_QUICKPLAY = 490
    BLOOD_HUNT_ASSASSIN_GAMES = 600
    DARK_STAR_SINGULARITY_GAMES = 610
    SUMMONER_S_RIFT_CLASH_GAMES = 700
    ARAM_CLASH_GAMES = 720
    CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_2 = 800
    CO_OP_VS_AI_INTRO_BOT_GAMES_2 = 810
    CO_OP_VS_AI_BEGINNER_BOT_GAMES_2 = 820
    CO_OP_VS_AI_INTRO_BOT_GAMES_3 = 830
    CO_OP_VS_AI_BEGINNER_BOT_GAMES_3 = 840
    CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_3 = 850
    CO_OP_VS_AI_INTRO_BOT_GAMES_4 = 870
    CO_OP_VS_AI_BEGINNER_BOT_GAMES_4 = 880
    CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_4 = 890
    ARURF_GAMES_2 = 900
    ASCENSION_GAMES_2 = 910
    LEGEND_OF_THE_PORO_KING_GAMES_2 = 920
    NEXUS_SIEGE_GAMES_2 = 940
    DOOM_BOTS_VOTING_GAMES = 950
    DOOM_BOTS_STANDARD_GAMES = 960
    STAR_GUARDIAN_INVASION_NORMAL_GAMES = 980
    STAR_GUARDIAN_INVASION_ONSLAUGHT_GAMES = 990
    PROJECT_HUNTERS_GAMES = 1000
    SNOW_ARURF_GAMES = 1010
    ONE_FOR_ALL_GAMES_2 = 1020
    ODYSSEY_EXTRACTION_INTRO_GAMES = 1030
    ODYSSEY_EXTRACTION_CADET_GAMES = 1040
    ODYSSEY_EXTRACTION_CREWMEMBER_GAMES = 1050
    ODYSSEY_EXTRACTION_CAPTAIN_GAMES = 1060
    ODYSSEY_EXTRACTION_ONSLAUGHT_GAMES = 1070
    TEAMFIGHT_TACTICS_GAMES = 1090
    RANKED_TEAMFIGHT_TACTICS_GAMES = 1100
    TEAMFIGHT_TACTICS_TUTORIAL_GAMES = 1110
    TEAMFIGHT_TACTICS_TEST_GAMES = 1111
    NEXUS_BLITZ_GAMES = 1200
    TEAMFIGHT_TACTICS_CHONCC_S_TREASURE_MODE = 1210
    NEXUS_BLITZ_GAMES_2 = 1300
    ULTIMATE_SPELLBOOK_GAMES = 1400
    ARENA = 1700
    ARENA_2 = 1710
    SWARM_MODE_GAMES = 1810
    SWARM = 1820
    SWARM_2 = 1830
    SWARM_3 = 1840
    PICK_URF_GAMES = 1900
    TUTORIAL_1 = 2000
    TUTORIAL_2 = 2010
    TUTORIAL_3 = 2020
    BRAWL = 2300
    ARAM_MAYHEM = 2400
    PRACTICE = 3140


QUEUE_DESCRIPTION: dict[Queue, str | None] = {
    Queue.ITEM_X: None,
    Queue.Q_5V5_BLIND_PICK_GAMES: '5v5 Blind Pick games',
    Queue.Q_5V5_RANKED_SOLO_GAMES: '5v5 Ranked Solo games',
    Queue.Q_5V5_RANKED_PREMADE_GAMES: '5v5 Ranked Premade games',
    Queue.CO_OP_VS_AI_GAMES: 'Co-op vs AI games',
    Queue.Q_3V3_NORMAL_GAMES: '3v3 Normal games',
    Queue.Q_3V3_RANKED_FLEX_GAMES: '3v3 Ranked Flex games',
    Queue.Q_5V5_DRAFT_PICK_GAMES: '5v5 Draft Pick games',
    Queue.Q_5V5_DOMINION_BLIND_PICK_GAMES: '5v5 Dominion Blind Pick games',
    Queue.Q_5V5_DOMINION_DRAFT_PICK_GAMES: '5v5 Dominion Draft Pick games',
    Queue.DOMINION_CO_OP_VS_AI_GAMES: 'Dominion Co-op vs AI games',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES: 'Co-op vs AI Intro Bot games',
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES: 'Co-op vs AI Beginner Bot games',
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES: 'Co-op vs AI Intermediate Bot games',
    Queue.Q_3V3_RANKED_TEAM_GAMES: '3v3 Ranked Team games',
    Queue.Q_5V5_RANKED_TEAM_GAMES: '5v5 Ranked Team games',
    Queue.CO_OP_VS_AI_GAMES_2: 'Co-op vs AI games',
    Queue.Q_5V5_TEAM_BUILDER_GAMES: '5v5 Team Builder games',
    Queue.Q_5V5_ARAM_GAMES: '5v5 ARAM games',
    Queue.ARAM_CO_OP_VS_AI_GAMES: 'ARAM Co-op vs AI games',
    Queue.ONE_FOR_ALL_GAMES: 'One for All games',
    Queue.Q_1V1_SNOWDOWN_SHOWDOWN_GAMES: '1v1 Snowdown Showdown games',
    Queue.Q_2V2_SNOWDOWN_SHOWDOWN_GAMES: '2v2 Snowdown Showdown games',
    Queue.Q_6V6_HEXAKILL_GAMES: '6v6 Hexakill games',
    Queue.ULTRA_RAPID_FIRE_GAMES: 'Ultra Rapid Fire games',
    Queue.ONE_FOR_ALL_MIRROR_MODE_GAMES: 'One For All: Mirror Mode games',
    Queue.CO_OP_VS_AI_ULTRA_RAPID_FIRE_GAMES: 'Co-op vs AI Ultra Rapid Fire games',
    Queue.DOOM_BOTS_RANK_1_GAMES: 'Doom Bots Rank 1 games',
    Queue.DOOM_BOTS_RANK_2_GAMES: 'Doom Bots Rank 2 games',
    Queue.DOOM_BOTS_RANK_5_GAMES: 'Doom Bots Rank 5 games',
    Queue.ASCENSION_GAMES: 'Ascension games',
    Queue.Q_6V6_HEXAKILL_GAMES_2: '6v6 Hexakill games',
    Queue.Q_5V5_ARAM_GAMES_2: '5v5 ARAM games',
    Queue.LEGEND_OF_THE_PORO_KING_GAMES: 'Legend of the Poro King games',
    Queue.NEMESIS_GAMES: 'Nemesis games',
    Queue.BLACK_MARKET_BRAWLERS_GAMES: 'Black Market Brawlers games',
    Queue.NEXUS_SIEGE_GAMES: 'Nexus Siege games',
    Queue.DEFINITELY_NOT_DOMINION_GAMES: 'Definitely Not Dominion games',
    Queue.ARURF_GAMES: 'ARURF games',
    Queue.ALL_RANDOM_GAMES: 'All Random games',
    Queue.Q_5V5_DRAFT_PICK_GAMES_2: '5v5 Draft Pick games',
    Queue.Q_5V5_RANKED_DYNAMIC_GAMES: '5v5 Ranked Dynamic games',
    Queue.Q_5V5_RANKED_SOLO_GAMES_2: '5v5 Ranked Solo games',
    Queue.Q_5V5_BLIND_PICK_GAMES_2: '5v5 Blind Pick games',
    Queue.Q_5V5_RANKED_FLEX_GAMES: '5v5 Ranked Flex games',
    Queue.Q_5V5_ARAM_GAMES_3: '5v5 ARAM games',
    Queue.Q_3V3_BLIND_PICK_GAMES: '3v3 Blind Pick games',
    Queue.Q_3V3_RANKED_FLEX_GAMES_2: '3v3 Ranked Flex games',
    Queue.SWIFTPLAY_GAMES: 'Swiftplay Games',
    Queue.NORMAL_QUICKPLAY: 'Normal (Quickplay)',
    Queue.BLOOD_HUNT_ASSASSIN_GAMES: 'Blood Hunt Assassin games',
    Queue.DARK_STAR_SINGULARITY_GAMES: 'Dark Star: Singularity games',
    Queue.SUMMONER_S_RIFT_CLASH_GAMES: "Summoner's Rift Clash games",
    Queue.ARAM_CLASH_GAMES: 'ARAM Clash games',
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_2: 'Co-op vs. AI Intermediate Bot games',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_2: 'Co-op vs. AI Intro Bot games',
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_2: 'Co-op vs. AI Beginner Bot games',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_3: 'Co-op vs. AI Intro Bot games',
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_3: 'Co-op vs. AI Beginner Bot games',
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_3: 'Co-op vs. AI Intermediate Bot games',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_4: 'Co-op vs. AI Intro Bot games',
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_4: 'Co-op vs. AI Beginner Bot games',
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_4: 'Co-op vs. AI Intermediate Bot games',
    Queue.ARURF_GAMES_2: 'ARURF games',
    Queue.ASCENSION_GAMES_2: 'Ascension games',
    Queue.LEGEND_OF_THE_PORO_KING_GAMES_2: 'Legend of the Poro King games',
    Queue.NEXUS_SIEGE_GAMES_2: 'Nexus Siege games',
    Queue.DOOM_BOTS_VOTING_GAMES: 'Doom Bots Voting games',
    Queue.DOOM_BOTS_STANDARD_GAMES: 'Doom Bots Standard games',
    Queue.STAR_GUARDIAN_INVASION_NORMAL_GAMES: 'Star Guardian Invasion: Normal games',
    Queue.STAR_GUARDIAN_INVASION_ONSLAUGHT_GAMES: 'Star Guardian Invasion: Onslaught games',
    Queue.PROJECT_HUNTERS_GAMES: 'PROJECT: Hunters games',
    Queue.SNOW_ARURF_GAMES: 'Snow ARURF games',
    Queue.ONE_FOR_ALL_GAMES_2: 'One for All games',
    Queue.ODYSSEY_EXTRACTION_INTRO_GAMES: 'Odyssey Extraction: Intro games',
    Queue.ODYSSEY_EXTRACTION_CADET_GAMES: 'Odyssey Extraction: Cadet games',
    Queue.ODYSSEY_EXTRACTION_CREWMEMBER_GAMES: 'Odyssey Extraction: Crewmember games',
    Queue.ODYSSEY_EXTRACTION_CAPTAIN_GAMES: 'Odyssey Extraction: Captain games',
    Queue.ODYSSEY_EXTRACTION_ONSLAUGHT_GAMES: 'Odyssey Extraction: Onslaught games',
    Queue.TEAMFIGHT_TACTICS_GAMES: 'Teamfight Tactics games',
    Queue.RANKED_TEAMFIGHT_TACTICS_GAMES: 'Ranked Teamfight Tactics games',
    Queue.TEAMFIGHT_TACTICS_TUTORIAL_GAMES: 'Teamfight Tactics Tutorial games',
    Queue.TEAMFIGHT_TACTICS_TEST_GAMES: 'Teamfight Tactics test games',
    Queue.NEXUS_BLITZ_GAMES: 'Nexus Blitz games',
    Queue.TEAMFIGHT_TACTICS_CHONCC_S_TREASURE_MODE: "Teamfight Tactics Choncc's Treasure Mode",
    Queue.NEXUS_BLITZ_GAMES_2: 'Nexus Blitz games',
    Queue.ULTIMATE_SPELLBOOK_GAMES: 'Ultimate Spellbook games',
    Queue.ARENA: 'Arena',
    Queue.ARENA_2: 'Arena',
    Queue.SWARM_MODE_GAMES: 'Swarm Mode Games',
    Queue.SWARM: 'Swarm',
    Queue.SWARM_2: 'Swarm',
    Queue.SWARM_3: 'Swarm',
    Queue.PICK_URF_GAMES: 'Pick URF games',
    Queue.TUTORIAL_1: 'Tutorial 1',
    Queue.TUTORIAL_2: 'Tutorial 2',
    Queue.TUTORIAL_3: 'Tutorial 3',
    Queue.BRAWL: 'Brawl',
    Queue.ARAM_MAYHEM: 'ARAM: Mayhem',
    Queue.PRACTICE: 'Practice Tool'
}


QUEUE_MAP: dict[Queue, str | None] = {
    Queue.ITEM_X: 'Custom games',
    Queue.Q_5V5_BLIND_PICK_GAMES: "Summoner's Rift",
    Queue.Q_5V5_RANKED_SOLO_GAMES: "Summoner's Rift",
    Queue.Q_5V5_RANKED_PREMADE_GAMES: "Summoner's Rift",
    Queue.CO_OP_VS_AI_GAMES: "Summoner's Rift",
    Queue.Q_3V3_NORMAL_GAMES: 'Twisted Treeline',
    Queue.Q_3V3_RANKED_FLEX_GAMES: 'Twisted Treeline',
    Queue.Q_5V5_DRAFT_PICK_GAMES: "Summoner's Rift",
    Queue.Q_5V5_DOMINION_BLIND_PICK_GAMES: 'Crystal Scar',
    Queue.Q_5V5_DOMINION_DRAFT_PICK_GAMES: 'Crystal Scar',
    Queue.DOMINION_CO_OP_VS_AI_GAMES: 'Crystal Scar',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES: "Summoner's Rift",
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES: "Summoner's Rift",
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES: "Summoner's Rift",
    Queue.Q_3V3_RANKED_TEAM_GAMES: 'Twisted Treeline',
    Queue.Q_5V5_RANKED_TEAM_GAMES: "Summoner's Rift",
    Queue.CO_OP_VS_AI_GAMES_2: 'Twisted Treeline',
    Queue.Q_5V5_TEAM_BUILDER_GAMES: "Summoner's Rift",
    Queue.Q_5V5_ARAM_GAMES: 'Howling Abyss',
    Queue.ARAM_CO_OP_VS_AI_GAMES: 'Howling Abyss',
    Queue.ONE_FOR_ALL_GAMES: "Summoner's Rift",
    Queue.Q_1V1_SNOWDOWN_SHOWDOWN_GAMES: 'Howling Abyss',
    Queue.Q_2V2_SNOWDOWN_SHOWDOWN_GAMES: 'Howling Abyss',
    Queue.Q_6V6_HEXAKILL_GAMES: "Summoner's Rift",
    Queue.ULTRA_RAPID_FIRE_GAMES: "Summoner's Rift",
    Queue.ONE_FOR_ALL_MIRROR_MODE_GAMES: 'Howling Abyss',
    Queue.CO_OP_VS_AI_ULTRA_RAPID_FIRE_GAMES: "Summoner's Rift",
    Queue.DOOM_BOTS_RANK_1_GAMES: "Summoner's Rift",
    Queue.DOOM_BOTS_RANK_2_GAMES: "Summoner's Rift",
    Queue.DOOM_BOTS_RANK_5_GAMES: "Summoner's Rift",
    Queue.ASCENSION_GAMES: 'Crystal Scar',
    Queue.Q_6V6_HEXAKILL_GAMES_2: 'Twisted Treeline',
    Queue.Q_5V5_ARAM_GAMES_2: "Butcher's Bridge",
    Queue.LEGEND_OF_THE_PORO_KING_GAMES: 'Howling Abyss',
    Queue.NEMESIS_GAMES: "Summoner's Rift",
    Queue.BLACK_MARKET_BRAWLERS_GAMES: "Summoner's Rift",
    Queue.NEXUS_SIEGE_GAMES: "Summoner's Rift",
    Queue.DEFINITELY_NOT_DOMINION_GAMES: 'Crystal Scar',
    Queue.ARURF_GAMES: "Summoner's Rift",
    Queue.ALL_RANDOM_GAMES: "Summoner's Rift",
    Queue.Q_5V5_DRAFT_PICK_GAMES_2: "Summoner's Rift",
    Queue.Q_5V5_RANKED_DYNAMIC_GAMES: "Summoner's Rift",
    Queue.Q_5V5_RANKED_SOLO_GAMES_2: "Summoner's Rift",
    Queue.Q_5V5_BLIND_PICK_GAMES_2: "Summoner's Rift",
    Queue.Q_5V5_RANKED_FLEX_GAMES: "Summoner's Rift",
    Queue.Q_5V5_ARAM_GAMES_3: 'Howling Abyss',
    Queue.Q_3V3_BLIND_PICK_GAMES: 'Twisted Treeline',
    Queue.Q_3V3_RANKED_FLEX_GAMES_2: 'Twisted Treeline',
    Queue.SWIFTPLAY_GAMES: "Summoner's Rift",
    Queue.NORMAL_QUICKPLAY: "Summoner's Rift",
    Queue.BLOOD_HUNT_ASSASSIN_GAMES: "Summoner's Rift",
    Queue.DARK_STAR_SINGULARITY_GAMES: 'Cosmic Ruins',
    Queue.SUMMONER_S_RIFT_CLASH_GAMES: "Summoner's Rift",
    Queue.ARAM_CLASH_GAMES: 'Howling Abyss',
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_2: 'Twisted Treeline',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_2: 'Twisted Treeline',
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_2: 'Twisted Treeline',
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_3: "Summoner's Rift",
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_3: "Summoner's Rift",
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_3: "Summoner's Rift",
    Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_4: "Summoner's Rift",
    Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_4: "Summoner's Rift",
    Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_4: "Summoner's Rift",
    Queue.ARURF_GAMES_2: "Summoner's Rift",
    Queue.ASCENSION_GAMES_2: 'Crystal Scar',
    Queue.LEGEND_OF_THE_PORO_KING_GAMES_2: 'Howling Abyss',
    Queue.NEXUS_SIEGE_GAMES_2: "Summoner's Rift",
    Queue.DOOM_BOTS_VOTING_GAMES: "Summoner's Rift",
    Queue.DOOM_BOTS_STANDARD_GAMES: "Summoner's Rift",
    Queue.STAR_GUARDIAN_INVASION_NORMAL_GAMES: 'Valoran City Park',
    Queue.STAR_GUARDIAN_INVASION_ONSLAUGHT_GAMES: 'Valoran City Park',
    Queue.PROJECT_HUNTERS_GAMES: 'Overcharge',
    Queue.SNOW_ARURF_GAMES: "Summoner's Rift",
    Queue.ONE_FOR_ALL_GAMES_2: "Summoner's Rift",
    Queue.ODYSSEY_EXTRACTION_INTRO_GAMES: 'Crash Site',
    Queue.ODYSSEY_EXTRACTION_CADET_GAMES: 'Crash Site',
    Queue.ODYSSEY_EXTRACTION_CREWMEMBER_GAMES: 'Crash Site',
    Queue.ODYSSEY_EXTRACTION_CAPTAIN_GAMES: 'Crash Site',
    Queue.ODYSSEY_EXTRACTION_ONSLAUGHT_GAMES: 'Crash Site',
    Queue.TEAMFIGHT_TACTICS_GAMES: 'Convergence',
    Queue.RANKED_TEAMFIGHT_TACTICS_GAMES: 'Convergence',
    Queue.TEAMFIGHT_TACTICS_TUTORIAL_GAMES: 'Convergence',
    Queue.TEAMFIGHT_TACTICS_TEST_GAMES: 'Convergence',
    Queue.NEXUS_BLITZ_GAMES: 'Nexus Blitz',
    Queue.TEAMFIGHT_TACTICS_CHONCC_S_TREASURE_MODE: 'Convergence',
    Queue.NEXUS_BLITZ_GAMES_2: 'Nexus Blitz',
    Queue.ULTIMATE_SPELLBOOK_GAMES: "Summoner's Rift",
    Queue.ARENA: 'Rings of Wrath',
    Queue.ARENA_2: 'Rings of Wrath',
    Queue.SWARM_MODE_GAMES: 'Swarm',
    Queue.SWARM: 'Swarm Mode Games',
    Queue.SWARM_2: 'Swarm Mode Games',
    Queue.SWARM_3: 'Swarm Mode Games',
    Queue.PICK_URF_GAMES: "Summoner's Rift",
    Queue.TUTORIAL_1: "Summoner's Rift",
    Queue.TUTORIAL_2: "Summoner's Rift",
    Queue.TUTORIAL_3: "Summoner's Rift",
    Queue.BRAWL: 'The Bandlewood',
    Queue.ARAM_MAYHEM: 'Howling Abyss',
    Queue.PRACTICE: "Summoner's Rift",
}
