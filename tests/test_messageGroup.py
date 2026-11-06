from conftest import RIOT_IDS, puuidFor, stateEntry
from messageGroup import messageGroup

SAME = "\N{EN DASH}"
UP = "\N{ESCAPE}[1;32m\N{BLACK UP-POINTING TRIANGLE}\N{ESCAPE}[0m"
DOWN = "\N{ESCAPE}[1;31m\N{BLACK DOWN-POINTING TRIANGLE}\N{ESCAPE}[0m"

# Today's ranks from the fake Riot API, as they'd be saved to state.json
TODAYS_STATE = {
    **stateEntry("SHEEP#NA1", "GOLD", "II", 40),
    **stateEntry("COW#NA1", "SILVER", "IV", 10),
    **stateEntry("WINNER#GAMER", "DIAMOND", "I", 75),
    **stateEntry("KOALA#NA1"),
}


def leaderboard(message):
    """The ranked lines of a posted message, without the timestamped header."""
    return message["content"].split("```ansi\n")[1]


def test_firstRunPostsLeaderboardAndSavesState(project, internet):
    assert messageGroup() == 1

    [post] = internet.rankedPosts
    assert leaderboard(post) == (
        f"{SAME} WINNER is DIAMOND I, 75 LP, and is the leader!\n"
        f"{SAME} SHEEP is GOLD II, 40 LP. 1335 LP behind the leader!\n"
        f"{SAME} COW is SILVER IV, 10 LP. 1965 LP behind the leader!\n"
        "\n"
        "KOALA is unranked!\n"
        "```"
    )
    assert project.readState() == TODAYS_STATE
    assert len(internet.accountLookups) == len(RIOT_IDS)


def test_withPreviousDayShowsMovementAndReusesPuuids(project, internet):
    project.setState(
        {
            **stateEntry("SHEEP#NA1", "GOLD", "II", 20),
            **stateEntry("COW#NA1", "SILVER", "III", 30),
            **stateEntry("WINNER#GAMER", "DIAMOND", "I", 75),
            **stateEntry("KOALA#NA1"),
        }
    )

    assert messageGroup() == 1

    [post] = internet.rankedPosts
    assert leaderboard(post) == (
        f"{SAME} WINNER is DIAMOND I, 75 LP, and is the leader!\n"
        f"{UP} SHEEP is GOLD II, 40 LP. 1335 LP behind the leader!\n"
        f"{DOWN} COW is SILVER IV, 10 LP. 1965 LP behind the leader!\n"
        "\n"
        "KOALA is unranked!\n"
        "```"
    )
    assert project.readState() == TODAYS_STATE
    assert internet.accountLookups == []


def test_withPreviousDayUnchangedDoesNotPost(project, internet):
    project.setState(TODAYS_STATE)

    assert messageGroup() == -1

    assert internet.rankedPosts == []
    assert project.readState() == TODAYS_STATE


def test_playerHittingRankedForTheFirstTimePosts(project, internet):
    project.setState({**TODAYS_STATE, **stateEntry("KOALA#NA1")})
    internet.ranked[puuidFor("KOALA#NA1")] = [{"tier": "IRON", "rank": "IV", "leaguePoints": 1}]

    assert messageGroup() == 1

    [post] = internet.rankedPosts
    assert f"{SAME} KOALA is IRON IV, 1 LP. 2774 LP behind the leader!\n" in leaderboard(post)
    assert "unranked" not in leaderboard(post)


def test_everyTierFromUnrankedToChallenger(project, internet):
    # Listed out of order in players.toml so the job has to sort them
    ladder = {
        "SHEEP#NA1": ("GOLD", "I", 10),
        "HEN#NA1": ("IRON", "IV", 5),
        "GOAT#NA1": ("CHALLENGER", "I", 1200),
        "KOALA#NA1": None,
        "DONKEY#NA1": ("EMERALD", "III", 25),
        "COW#NA1": ("SILVER", "II", 60),
        "LLAMA#NA1": ("MASTER", "I", 150),
        "DUCK#NA1": ("BRONZE", "III", 30),
        "ALPACA#NA1": ("DIAMOND", "II", 50),
        "PIG#NA1": ("PLATINUM", "IV", 80),
        "HORSE#NA1": ("GRANDMASTER", "I", 600),
    }
    project.setPlayers(list(ladder))
    internet.ranked = {
        puuidFor(riotId): [] if rank is None else [{"tier": rank[0], "rank": rank[1], "leaguePoints": rank[2]}]
        for riotId, rank in ladder.items()
    }

    assert messageGroup() == 1

    [post] = internet.rankedPosts
    assert leaderboard(post) == (
        f"{SAME} GOAT is CHALLENGER, 1200 LP, and is the leader!\n"
        f"{SAME} HORSE is GRANDMASTER, 600 LP. 600 LP behind the leader!\n"
        f"{SAME} LLAMA is MASTER, 150 LP. 1050 LP behind the leader!\n"
        f"{SAME} ALPACA is DIAMOND II, 50 LP. 1350 LP behind the leader!\n"
        f"{SAME} DONKEY is EMERALD III, 25 LP. 1875 LP behind the leader!\n"
        f"{SAME} PIG is PLATINUM IV, 80 LP. 2320 LP behind the leader!\n"
        f"{SAME} SHEEP is GOLD I, 10 LP. 2490 LP behind the leader!\n"
        f"{SAME} COW is SILVER II, 60 LP. 2940 LP behind the leader!\n"
        f"{SAME} DUCK is BRONZE III, 30 LP. 3470 LP behind the leader!\n"
        f"{SAME} HEN is IRON IV, 5 LP. 3995 LP behind the leader!\n"
        "\n"
        "KOALA is unranked!\n"
        "```"
    )
