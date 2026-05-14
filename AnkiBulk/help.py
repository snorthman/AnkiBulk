from __future__ import annotations

from aqt.qt import (
    QDialog,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    Qt,
    qconnect,
)

from .i18n import tr


def _element(key: str, *args, **kwargs) -> str:
    tags = (' ' + ' '.join([f'{k}="{v}"' for k, v in kwargs.items()])) if kwargs else ''
    if not args:
        return f'<{key}{tags}/>'
    return f'<{key}{tags}>{"\n".join(args)}</{key}>'


def _element_table(*args: str, **kwargs) -> str:
    table = []
    for col1, col2 in [args[i:i + 2] for i in range(0, len(args), 2)]:
        col1 = _element('td', _element('b', col1))
        col2 = _element('td', col2)
        table.append(_element('tr', col1 + col2))
    return _element('table', *table, **kwargs)


def _html() -> str:
    github = "https://github.com/snorthman/AnkiBulk"
    return '\n'.join([
        _element('p', tr("help-intro")),
        '',
        _element('h3', tr("help-selection-heading")),
        _element('p', tr("help-selection-desc")),
        '',
        _element('h3', tr("help-table-heading")),
        _element('p', tr("help-table-desc")),
        _element_table(
            tr("table-insert-clipboard"), tr("help-table-insert-clipboard"),
            tr("table-update-from-selection"), tr("help-table-update-selection"),
            tr("help-table-right-click-header"), tr("help-table-right-click-header-desc"),
            "Enter", tr("help-table-enter"),
            "Delete", tr("help-table-delete"),
            "Backspace", tr("help-table-backspace"),
            cellpadding=1
        ),
        '',
        _element('h3', tr("help-text-heading")),
        _element('p', tr("help-text-desc")),
        _element_table(
            tr("text-options"), tr("help-text-options"),
            tr("text-copy-to-clipboard"), tr("help-text-copy"),
            cellpadding=1
        ),
        '',
        _element('h3', tr("help-bulk-add-heading")),
        _element('p', tr("help-bulk-add-desc")),
        '',
        _element('hr'),
        _element('p', *[
            _element('a', tr("help-link-issues"), href=f'{github}/issues'), '&middot;',
            _element('a', tr("help-link-discussions"), href=f'{github}/discussions'), '&middot;',
            _element('a', tr("help-link-github"), href=github),
        ])
    ])


class Dialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("help-title"))
        self.setMinimumWidth(700)

        layout = QVBoxLayout()
        self.setLayout(layout)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("background-color: #F3F3F3; border: 0px;")
        browser.setHtml(_html())

        doc = browser.document()
        doc.setTextWidth(browser.viewport().width())
        browser.setFixedHeight(int(doc.size().height()) + 2 * browser.frameWidth())

        layout.addWidget(browser)

        close_button = QPushButton(tr("btn-close"))
        close_button.setAutoDefault(True)
        qconnect(close_button.clicked, self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
