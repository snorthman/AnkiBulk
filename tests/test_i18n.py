import re

from AnkiBulk.i18n import i18n


def test_i18n(monkeypatch):
    tr = i18n()
    r = re.compile(r'\{(\w+)}')

    fails = []
    for lang in tr.base.iterdir():
        monkeypatch.setattr(i18n, 'get_locale', property(lambda self: lang.stem))
        for key in tr:
            entry = tr[key]
            try:
                if isinstance(entry, dict):
                    assert tr.tr(key, n=1) is not None
                    assert tr.tr(key, n=2) is not None
                elif isinstance(entry, str):
                    assert tr.tr(key) is not None

                    entry_kwargs = {kwarg: f'test{i}' for i, kwarg in enumerate(r.findall(entry))}
                    entry_fmt = tr.format(entry, **entry_kwargs)
                    assert r.findall(entry_fmt) == []
                else:
                    assert entry is not None
            except AssertionError:
                fails.append(f'lang={lang.stem}, key={key}, entry={entry!r}')

    assert not fails, '\n'.join(fails)