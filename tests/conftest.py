from __future__ import annotations

import importlib.util
import os
import tempfile
import shutil
import sys
import time
import zipfile
from pathlib import Path

import pytest

# noinspection PyTypeChecker
REPO_PATH = Path(importlib.util.find_spec('AnkiBulk').origin).parent.parent
TESTS_PATH = REPO_PATH / 'tests'
PROFILE_PATH = Path(os.environ['APPDATA']) / 'Anki2' / 'AnkiSenseiTest'
COLLECTION_PATH = PROFILE_PATH / 'collection.anki2'
ADDON_DIR = Path(os.environ['APPDATA']) / 'Anki2' / 'addons21' / 'AnkiBulk'
ADDON_BACKUP_DIR = ADDON_DIR.with_name('AnkiBulk.testbak')
ANKI_SITE_PACKAGES_PATH = (Path(os.environ['LOCALAPPDATA'])) / 'AnkiProgramFiles' / '.venv' / 'Lib' / 'site-packages'
if str(ANKI_SITE_PACKAGES_PATH) not in sys.path:
    sys.path.insert(0, str(ANKI_SITE_PACKAGES_PATH))


def _colpkg_path(name: str) -> Path:
    path = TESTS_PATH / 'collections' / f'{name}.colpkg'
    if not path.exists():
        raise FileNotFoundError(f'No collection found at {path}')
    return path


def _build_collection(*collection: str):
    """
    Build a merged collection from one or more named .colpkg files into dest.
    The first collection is used as the base; subsequent ones are imported
    into it using Anki's importer so notes and decks are merged properly.
    """
    if collection:
        import anki.lang
        from anki.collection import Collection
        from anki.importing.apkg import AnkiPackageImporter

        colpkgs = [TESTS_PATH / 'collections' / f'{name}.colpkg' for name in collection]
        for colpkg in colpkgs:
            assert colpkg.exists(), f'Collection {colpkg} does not exist'

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with zipfile.ZipFile(colpkgs[0]) as zf:
                src_name = next((n for n in ('collection.anki21', 'collection.anki2') if n in zf.namelist()), None)
                if src_name is None:
                    raise FileNotFoundError(f'No collection DB found inside {colpkgs[0].name}')
                col_path = tmp_dir / 'collection.anki2'
                col_path.write_bytes(zf.read(src_name))

            try:
                col = Collection(str(col_path))
                if anki.lang.current_i18n is None:
                    anki.lang.current_i18n = col._backend

                for colpkg in colpkgs[1:]:
                    colpkg_tmp = tmp_dir / colpkg.name
                    with zipfile.ZipFile(colpkg) as zf, zipfile.ZipFile(colpkg_tmp, 'w', zipfile.ZIP_DEFLATED) as out:
                        for item in zf.infolist():
                            if item.filename != 'media':
                                out.writestr(item, zf.read(item.filename))
                        out.writestr('media', '{}')
                    imp = AnkiPackageImporter(col, str(colpkg))
                    imp.run()
            finally:
                col.close()

            shutil.copy2(tmp_dir / 'collection.anki2', COLLECTION_PATH)


@pytest.fixture
def anki(tmp_path):
    import aqt

    if str(REPO_PATH) not in sys.path:
        sys.path.insert(0, str(REPO_PATH))

    _original_all_addons = aqt.addons.AddonManager.allAddons

    def _patched_all_addons(self):
        addons = _original_all_addons(self)
        if 'AnkiBulk' not in addons:
            addons.append('AnkiBulk')
        return addons

    def _patched_load_addons(self):
        from aqt.addons import AbortAddonImport
        for addon in self.all_addon_meta():
            if not addon.enabled or not addon.compatible():
                continue
            self.dirty = True
            try:
                __import__(addon.dir_name)
            except AbortAddonImport:
                pass

    aqt.addons.AddonManager.allAddons = _patched_all_addons
    aqt.addons.AddonManager.loadAddons = _patched_load_addons

    # Anki's ErrorHandler (which replaces sys.stderr) has no flush() method,
    # causing PyCharm's debug console to crash when evaluating expressions.
    import aqt.errors
    if not hasattr(aqt.errors.ErrorHandler, 'flush'):
        aqt.errors.ErrorHandler.flush = lambda self: None

    _slot_exception: list[BaseException] = []
    _original_excepthook = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        _slot_exception.append(exc_value)
        aqt.qt.QApplication.instance().exit(1)

    sys.excepthook = _excepthook

    snapshot = COLLECTION_PATH.with_suffix('.anki2.bak')
    shutil.copy2(COLLECTION_PATH, snapshot)
    os.environ['ANKIDEV'] = '1'

    # Anki's config machinery (getConfig/writeConfig) looks in addons21/<pkg>/
    # regardless of how the code was loaded. Create an ephemeral addon dir with
    # our shipped config.json so meta.json can be written there during the run.
    # If the user has a real AnkiBulk install, rename it aside first so tests
    # can't clobber real settings.
    if ADDON_BACKUP_DIR.exists():
        raise RuntimeError(
            f'Stale backup at {ADDON_BACKUP_DIR}. Previous teardown did not '
            f'complete (likely a Windows file lock from Anki not fully releasing '
            f'collection.anki2, or a .pyc in __pycache__ blocking rmtree). '
            f'Rename back to "AnkiBulk" manually.'
        )
    if ADDON_DIR.exists():
        ADDON_DIR.rename(ADDON_BACKUP_DIR)
    ADDON_DIR.mkdir(parents=True, exist_ok=True)

    def run(*collections: str, config: str = None, response: Path = None):
        """
        Launch Anki against the AnkiSenseiTest profile.

        collections: zero or more .colpkg filenames (without extension) from
            tests/collections/ to merge into the profile collection before launch.
        config: optional filename from tests/configs/ to install as the addon's
            config.json. Defaults to the package's shipped config.json.
        response: optional path to a JSON file to install as the addon's
            response1.json. When present (and ANKIDEV=1), the reviewer uses
            this instead of making a real LLM call.
        """
        if config:
            shutil.copy2((TESTS_PATH / 'configs' / config).with_suffix('.json'), ADDON_DIR / 'config.json')
        else:
            shutil.copy2(REPO_PATH / 'AnkiBulk' / 'config.json', ADDON_DIR / 'config.json')
        if response:
            shutil.copy2((TESTS_PATH / 'responses' / response).with_suffix('.json'), ADDON_DIR / 'response.json')
        _build_collection(*collections)
        aqt._run(['anki', '--profile', 'AnkiSenseiTest'])
        if _slot_exception:
            raise _slot_exception[0]

    try:
        yield run
    finally:
        # Always restore, even if setup/run raised. Each step is defensive:
        # Qt background threads on Windows can keep collection.anki2 and
        # __pycache__/*.pyc locked briefly after aqt._run() returns, so we
        # retry the fragile filesystem ops rather than let one failure
        # strand the AnkiBulk.testbak backup.
        sys.excepthook = _original_excepthook

        for _ in range(5):
            try:
                shutil.copy2(snapshot, COLLECTION_PATH)
                break
            except PermissionError:
                time.sleep(0.2)
        try:
            snapshot.unlink(missing_ok=True)
        except OSError:
            pass

        shutil.rmtree(ADDON_DIR, ignore_errors=True)
        for _ in range(5):
            if not ADDON_DIR.exists():
                break
            try:
                shutil.rmtree(ADDON_DIR)
            except OSError:
                time.sleep(0.2)

        if ADDON_BACKUP_DIR.exists() and not ADDON_DIR.exists():
            ADDON_BACKUP_DIR.rename(ADDON_DIR)
