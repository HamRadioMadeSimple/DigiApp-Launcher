# Light and dark themes - the standard for the station apps

DigiApp Launcher is the first app built this way; the other apps (RigPanel, JS8FastChat, FCC Lookup, ...) should
follow the same pattern so they look and behave alike.

## What the user sees
- A **`☀ Light Theme`** / **`☾ Dark Theme`** button, styled exactly like the app's other buttons (same colours, bold,
  same size), placed at the end of a button row where it is easy to see - in DigiApp Launcher at the right of the
  + Add App ... Find Missing Apps row. (A small, plain button in the header was too faint to notice.)
- One click saves everything, closes the window and reopens it in the other look (about a second). No settings page.
- The choice is remembered in the app's own settings file. New installs and older settings files start **Dark**.
- Every window the app draws follows the theme, including the Windows title bar (dark title bar only in Dark).
  Pop-up questions drawn by the system (file dialogs, yes/no boxes) keep the system's own look.

## How it is built
- **One colour table per theme, same keys in both** (`THEMES = {'Dark': {...}, 'Light': {...}}`). No colour is
  written anywhere else in the code - widgets always use `C['Key']`. A self-test checks both tables have the same keys.
- **`set_theme(name)`** fills the shared table `C` before any window is made (in `main()`, right after the settings load).
- **Fill colours and text colours are separate keys.** Bright green/yellow/orange work as *button fills* in both
  themes (with black text), but as *text* on a white background they can't be read. So text uses `GreenText`,
  `YellowText`, `OrangeText`: bright in Dark, darkened in Light. Use the fill key for backgrounds, the Text key for words.
- **Switching = restart the window**, not repaint every widget: save, write the new theme, start a new copy of the
  app, close this one. Simple, and nothing can be left half-painted.
- Setting key: `"Theme": "Dark" | "Light"` - added, never renamed (old files simply lack it).
- Windows title bar: `DwmSetWindowAttribute(hwnd, 20 (or 19 on older Windows 10), dark ? 1 : 0)`.
- **Tick marks:** a tick on a coloured box must contrast with that box - black on bright green, but on a darker
  blue box (Light theme) the tick is white. Give each box colour its own tick key (`BlueTick`).

## Fonts (same rule in every app)
- **One font family for the whole window**: Segoe UI on Windows, Ubuntu / DejaVu Sans on Linux. No typewriter
  font (Consolas, DejaVu Sans Mono) for paths, status lines or readouts - it looked out of place.
- A few sizes only: 10 for text and buttons, 11 for emphasis (profile name, tips, header readouts), 13 for the big
  action buttons, 20 for the title.
- Small text people need to read - file paths, status lines, numbers - is **bold**; plain 10 pt was too faint,
  especially in the Light theme.

## The palettes (DigiApp Launcher)
| Key | Dark | Light | Used for |
|---|---|---|---|
| Header | #070B14 | #DCE3EE | top banner |
| Bg | #0D1626 | #F3F5F9 | window background |
| Field | #0A1220 | #FFFFFF | list background |
| RowAlt | #101B2E | #EEF2F8 | every other row |
| Head | #2B3649 | #D5DCE8 | column headers, plain buttons |
| Text | #E8ECF3 | #141C2B | normal text |
| Dim | #8E9AB0 | #5B6678 | secondary text |
| Select | #2F6DB5 | #2F6DB5 | selected row (white text) |
| Green / Yellow / Orange | #3DF58A / #F5DC4E / #F5A524 | #3DDC84 / #F5D53B / #F5A524 | button fills (black text) |
| GreenText / YellowText / OrangeText | same as fills | #0B7A3B / #7A5C00 / #A85A00 | status, tips, readouts |
| Halt | #A51D1D | #B42318 | STOP button (white text) |
| Missing / MissText | #4A1D27 / #FFB8B8 | #FBE1E4 / #A3161D | a program that can't be found |
| PathText | #CFD8E6 | #1E2A40 | program locations (bold) |
| BlueTick | #05080F | #FFFFFF | tick on the blue Minimize box |

Check a new light colour for contrast against `Bg` and `Field` before using it for text (aim for 4.5 : 1 or more).
