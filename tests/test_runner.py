import pytest
import requests

from config import PERSONAL_EMAIL
from conftest import puuidFor, stateEntry


@pytest.fixture
def yesterday(project):
    """Saved state from a previous run: SHEEP has since gained LP and patch 25-22 has since come out."""
    project.setState(
        {
            **stateEntry("SHEEP#NA1", "GOLD", "II", 20),
            **stateEntry("COW#NA1", "SILVER", "IV", 10),
            **stateEntry("WINNER#GAMER", "DIAMOND", "I", 75),
            **stateEntry("KOALA#NA1"),
        }
    )
    project.patchFile.write_text("25-21")


def assertEmailedFailure(internet):
    assert len(internet.emails) == 1
    email = internet.emails[0]
    assert email["Subject"] == "Ranked Race Job Failed"
    assert email["To"] == PERSONAL_EMAIL
    assert "Traceback" in email.get_content()


def test_standardRunPostsBothJobsWithoutEmailing(yesterday, project, internet, runJobs):
    runJobs()

    assert len(internet.rankedPosts) == 1
    assert len(internet.newsPosts) == 1
    assert internet.hostDms == []
    assert internet.emails == []


@pytest.mark.parametrize("hasSavedState", [True, False], ids=["with-saved-state", "first-run"])
def test_debugRunOnlyMessagesTheHost(project, internet, runJobs, request, hasSavedState):
    if hasSavedState:
        request.getfixturevalue("yesterday")
    savedFiles = {path: path.read_text() for path in (project.stateFile, project.patchFile) if path.exists()}

    runJobs(debug=True)

    # Every POST went to opening or messaging the host's DM, nothing to a public channel
    for method, url, _ in internet.requests:
        if method == "POST":
            assert url.endswith("/users/@me/channels") or "/channels/dm-channel/" in url, url
    assert len(internet.hostDms) == 2
    assert internet.rankedPosts == []
    assert internet.newsPosts == []
    assert internet.emails == []
    # Saved state is left alone so the real run still sees the changes
    assert {path: path.read_text() for path in (project.stateFile, project.patchFile) if path.exists()} == savedFiles


def test_riotApiErrorEmailsAndPatchJobStillRuns(yesterday, project, internet, runJobs):
    savedState = project.readState()
    internet.ranked[puuidFor("SHEEP#NA1")] = 503

    runJobs()

    assertEmailedFailure(internet)
    assert internet.rankedPosts == []
    assert project.readState() == savedState
    assert len(internet.newsPosts) == 1


def test_rankedJobCrashEmails(yesterday, project, internet, runJobs):
    project.setPlayers(["SHEEP#NA1", "NO-TAGLINE"])

    runJobs()

    assertEmailedFailure(internet)
    assert internet.rankedPosts == []


def test_patchJobCrashEmails(project, internet, runJobs):
    project.setState(
        {
            **stateEntry("SHEEP#NA1", "GOLD", "II", 40),
            **stateEntry("COW#NA1", "SILVER", "IV", 10),
            **stateEntry("WINNER#GAMER", "DIAMOND", "I", 75),
            **stateEntry("KOALA#NA1"),
        }
    )
    internet.versions = requests.exceptions.ConnectionError("Data Dragon is down")

    runJobs()

    assertEmailedFailure(internet)
    assert internet.newsPosts == []
    assert not project.patchFile.exists()


def test_patchNotOutYetIsNotAFailure(yesterday, project, internet, runJobs):
    internet.patchPages = {}

    runJobs()

    assert internet.emails == []
    assert internet.newsPosts == []
    assert project.patchFile.read_text() == "25-21"
