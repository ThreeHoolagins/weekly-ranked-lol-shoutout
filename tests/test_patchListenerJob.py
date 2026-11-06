import json

import pytest

from conftest import PATCH_IMAGE, PATCH_TAGLINE
from patchListenerJob import PatchNotPostedException, checkForPatch, getPatchNotesUrl
from riotApiConstants import DATA_DRAGON_VERSIONS_URL


def test_postsNextPatchWhenPageIsUp(project, internet):
    project.patchFile.write_text("25-21")

    checkForPatch()

    [post] = internet.newsPosts
    posted = json.dumps(post)
    assert "Patch 25.22 has landed" in posted
    assert PATCH_TAGLINE in posted
    assert PATCH_IMAGE in posted
    assert getPatchNotesUrl("25-22") in posted
    assert project.patchFile.read_text() == "25-22"


def test_doesNotPostWhenPageIsMissing(project, internet):
    project.patchFile.write_text("25-22")

    with pytest.raises(PatchNotPostedException):
        checkForPatch()

    assert internet.newsPosts == []
    assert project.patchFile.read_text() == "25-22"


def test_withNoSavedPatchFallsBackToDataDragonVersions(project, internet):
    assert not project.patchFile.exists()

    checkForPatch()

    assert ("GET", DATA_DRAGON_VERSIONS_URL, None) in internet.requests
    [post] = internet.newsPosts
    assert "Patch 25.22 has landed" in json.dumps(post)
    assert project.patchFile.read_text() == "25-22"
