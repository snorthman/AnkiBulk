# AnkiBulk

An Anki addon for quickly adding many notes at once.

Type words into the sort field column, one per row, then switch to Text view to copy everything to your clipboard. Paste it into an LLM, spreadsheet, or any other tool to fill in the remaining fields. When you're done, paste the result back and click Bulk Add.

## Screenshots

<img width="890" height="621" alt="image" src="https://github.com/user-attachments/assets/5ad5c5af-ec68-499d-b4e5-91969acbf743" />
<img width="890" height="621" alt="image" src="https://github.com/user-attachments/assets/106217c9-9770-4372-b36f-de6cc42ae358" />

## Installation

1. Open Anki and go to **Tools > Add-ons > Get Add-ons**.
2. Paste the add-on code and restart Anki.

## Usage

### Browser selection

Select one or more cards in the browser before opening AnkiBulk. The first card's notetype determines the table columns, and all selected notes appear as read-only example rows (grey). These examples give context when filling in new notes — for instance, an LLM can see your existing cards and match the style. If nothing is selected, you can choose any notetype manually.

Open AnkiBulk from the browser menu: **AnkiBulk > Bulk Add**.

### Table view

The table shows existing notes (read-only, grey) and new notes (editable, white). Right-click a column header to show or hide columns. Right-click a cell for the full context menu.

| Action | Shortcut | Description |
|--------|----------|-------------|
| Copy | Ctrl+C | Copy selected cells to clipboard |
| Paste | Ctrl+V | Paste clipboard into selected cells, adding rows as needed |
| Undo / Redo | Ctrl+Z / Ctrl+Y | Undo or redo table changes |
| Insert Row | Enter | Insert a new row below the current one |
| Delete Row | Delete | Remove the selected editable row |
| Update from Selection | Ctrl+R | Refresh example rows from the current browser selection |
| Tab / Shift+Tab | | Move between cells; Tab on the last cell of the last row adds a new row |
| Backspace | | Clear the sort field, or remove the row if already empty |

### Text view

Toggle to Text view to edit notes in YAML format. The top pane shows your selected example notes (read-only); the bottom pane is for your new notes. Switching back to Table view validates and applies the YAML.

| Action | Shortcut | Description |
|--------|----------|-------------|
| Copy to Clipboard | Ctrl+Shift+C | Copy content in the chosen format (YAML, JSON, XML, CSV, or TSV) |
| Settings | | Configure copy format, whether to include example notes, and additional text |

### Bulk Add

Click **Bulk Add** to create notes from all editable rows that have content in the sort field. Notes are added to the selected deck. The browser updates to show the newly created notes.

## Contribute

- [Report an issue](https://github.com/snorthman/AnkiBulk/issues)
- [Suggestions & discussion](https://github.com/snorthman/AnkiBulk/discussions)

_Tested extensively with Anki version 25.09; your results may vary for earlier versions._

**All non-English languages are currently machine translated. Feel free to pull request translation fixes.**

## Donate

Was this useful? Consider buying me a coffee!

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/H2H7PIMZR)
