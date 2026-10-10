# English and Vietnamese

Choose **Tiếng Việt** or **English** on the welcome screen, or change the language in
**Settings → Appearance & language**. The choice applies immediately and is saved for the
next launch. Minecraft account sign-in, game data and installed content are unaffected.

The launcher translates its navigation, dialogs, guides, status messages, recognized
errors and native tray menu. Project names and descriptions supplied by Modrinth,
CurseForge or Hangar, player names, chat, file paths and raw game logs retain their source
text. Guide GIFs illustrate recorded example interactions; the written guide beside each
GIF follows the selected language. Prices remain in VND in both languages.

## Maintaining translations

Both bundled catalogs live in `src/nostalgia/ui/qml/i18n/`. No translation service or
network access is needed. Keep identical keys in `en.json` and `vi.json`:

- Existing symbolic keys use `Tr.text(key)`.
- Labels use `Tr.phrase(source)`. Modern components import `"../" as Legacy` and use
  `Legacy.Tr.phrase(source)`.
- Sentences with values use `Tr.format(source, values)` and `%1`, `%2`, etc. Translators can
  reorder values without translating the values themselves.
- Known Python status/error templates use `m:` keys with numbered `{0}` placeholders.
  `Tr.message(source)` matches the whole template and keeps captured values intact.
  Only pass launcher messages to this function, never game logs, chat or user names.
- Catalog aliases for rendered English labels allow already-open dialogs to switch back
  to Vietnamese. When changing a template, update its alias too; do not reuse a technical
  identifier as a translated presentation label.
- Guide content remains in `preview/GuideCatalog.js`; `Guides.find(topicId, Legacy.Tr)`
  returns a translated view without changing topic IDs or GIF filenames.
- Dropdown display labels are separate from values saved to configuration. For example,
  server game modes still save `survival`, `creative`, `adventure` or `spectator`.

`test_localization_catalogs.py` checks key parity, placeholder parity, duplicate keys,
QML label coverage and guide coverage. `test_live_localization.py` exercises welcome
selection, persistence, page switching, open dialogs, guide search labels, errors,
parameter preservation and the native tray menu.
