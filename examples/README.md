# Example profiles

`example_settings.json` shows two typical profiles (a JS8 net and Fldigi messaging) in the
format DigiApp Launcher saves. It is a reference for testing and documentation - the program
never loads it on its own, so a new user still starts with one empty "My Profile".

To try it on a test machine (this REPLACES that machine's profiles):

| System  | Copy it to |
|---------|------------|
| Linux   | `~/.config/digiapp-launcher/settings.json` |
| Windows | `%APPDATA%\DigiApp Launcher\settings.json` |

On Linux, `"Path": "flrig"` finds the program on the system path; on Windows use full paths such as
`C:\\Flrig\\flrig-2.0.10\\flrig.exe`. Click **Find Missing Apps** to fill in any that are red.
