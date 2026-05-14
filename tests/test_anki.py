import pytest


@pytest.mark.interactive
@pytest.mark.anki
def test_anki_interactive(anki):
    """
    Launches Anki with the AnkiSenseiTest profile and the addon symlinked in.
    Interact manually, then close Anki to pass the test.
    """
    anki()
