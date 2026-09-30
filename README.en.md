# omarchy-rus

🌐 [Русский](README.md) · **English**

Russian localization for Omarchy (Arch + Hyprland): locale, UI translation, keyboard layout, speech input, Russian Ministry
root certificates and other Russia-specific extras. Everything is a set of independent **modules**; when you run `install.sh`
you assemble a "basket" of the ones you want.

## Quick start
    ./install.sh                # interactive: "Recommended" / "Everything" / "Pick manually"
    ./install.sh --list         # module catalog with descriptions
    ./install.sh --all          # everything, including optional (e-signature, Ministry certificates)
    ./install.sh -y             # recommended only, no prompts
    ./install.sh --only timezone,telegram     # only the given ids (see --list)
    ./install.sh --skip voxtype,tts           # recommended, except the given ones
    ./install.sh --dry-run ...  # print what would run and exit

Selection UI: `gum` (ships with Omarchy; Space toggles, Ctrl+A selects all), with a plain text menu as fallback.
Modules that need `sudo` ask for the password once. A failing module does not stop the rest; a summary is printed at the end.
The Omarchy shell is restarted once at the end if panels were changed. Log out and back in afterwards.

## Modules
| id | Group | Default | What it does |
|----|-------|:---:|------------|
| `locale` | Base | ✓ | `ru_RU.UTF-8` locale, `LANG`, `us,ru` layout (Left Alt + Right Alt) |
| `hypr-layout` | Base | ✓ | `us,ru` in `~/.config/hypr/input.lua` (with backup), Hyprland reload |
| `spell` | Base | ✓ | `hunspell-ru`, `aspell-ru`, `man-pages-ru` |
| `timezone` | Simple | ✓ | timezone (`Europe/Moscow`, `RUS_TZ` variable) and `ru.pool.ntp.org` for timesyncd |
| `xcompose` | Simple | ✓ | block in `~/.XCompose`: `₽` `№` `«»` `—` `–` `…` (Compose = Caps Lock) |
| `vconsole-font` | Simple | ✓ | Cyrillic TTY font (`LatArCyrHeb-16`), takes effect after reboot |
| `office` | Simple | ✓ | LibreOffice: Russian pack, hyphenation, thesaurus (if LibreOffice is installed) |
| `telegram` | Apps | ✓ | `telegram-desktop` |
| `weather` | Apps | ✓ | weather widget: `unit=metric`, translation, Russian city geocoding |
| `voxtype` | Apps | ✓ | Russian speech recognition (Parakeet), see below |
| `panels` | UI | ✓ | translates panels and overlays (plugin clones), see below |
| `menu` | UI | ✓ | translates the Omarchy menu |
| `fastfetch` | UI | ✓ | `~/.config/fastfetch/config.jsonc` with Russian headings ("About") |
| `tts` | UI | ✓ | `speech-dispatcher` + `espeak-ng`, Russian as the default language |
| `ecp` | Work | — | PC/SC for e-signatures: `pcsclite`, `ccid`, `opensc`, `pcsc-tools`, `pcscd` |
| `mincifry` | Work | — | Ministry certificates + weekly expiry check |

```mermaid
flowchart TD
    I["install.sh"] --> S{"Selection"}
    S -->|"Recommended / -y"| D["Default modules"]
    S -->|"Everything / --all"| A["All modules"]
    S -->|"Manual / --only"| U["Chosen modules"]
    D --> R["Run modules/NN-name.sh in numeric order"]
    A --> R
    U --> R
    R --> X["Restart the Omarchy shell (once, if panels were touched)"]
    X --> Y["Summary: what passed, what failed"]
    C["install-mincifry-ca.sh"] -.->|"mincifry module"| R
    M["translate-menu.py"] -.->|"menu module"| R
    T["translate-plugins.py"] -.->|"panels and weather modules"| R
```

## Project layout
| File | Purpose |
|------|---------|
| `install.sh` | orchestrator: module selection, sudo, execution, summary |
| `modules/NN-name.sh` | modules; metadata in the header (`title`, `group`, `default`, `sudo`, `desc`). Drop your own file here to add one |
| `translate-menu.py` | translates the Omarchy menu |
| `translate-plugins.py` | translates bar plugins; `./translate-plugins.py [name…] [--except name…]` |
| `install-mincifry-ca.sh` | Ministry certificates and expiry monitoring |
| `input.lua.snippet` | snippet appended to `~/.config/hypr/input.lua` |

## Deliberately not included
- **Russian pacman mirrors.** Omarchy uses its own "stable" mirror `stable-mirror.omarchy.org`, which pins package versions;
  replacing `mirrorlist` (e.g. via `reflector`) would break that model.
- **Screensaver and "About" text.** `about.txt`/`screensaver.txt` are ASCII logos; nothing to translate.
- **Lock screen and the polkit dialog.** Authentication plugins are not cloned: a bug in a clone could lock you out.
- **CryptoPro CSP, Rutoken/JaCarta drivers, 1C** are proprietary and need registration; the `ecp` module installs only the
  open part (PC/SC) and prints links.

## Notes
- Fonts (Noto, Liberation) already support Cyrillic; `fcitx5` is installed.
- Firefox: `omarchy pkg add firefox-i18n-ru`. Chromium and LibreOffice take their language from the system
  (LibreOffice may need a separate language pack).
- To keep the English UI but type in Russian, remove the `LANG` step.
- Files in `/usr/share/omarchy/` are never touched — only `~/.config/`.

## voxtype (voice input)
`install.sh` enables the ONNX build of voxtype (`sudo voxtype setup onnx --enable`), downloads
`parakeet-tdt-0.6b-v3-int8` (multilingual, Russian supported) and switches to `engine = "parakeet"` only after a
successful download. GigaAM is not supported in voxtype 1.1.0 (a possible route is an external server via `whisper-mode = remote`).
Known issue: `models.voxtype.io` can serve the ~650 MB file very slowly; on failure the script fetches the same files from the
Hugging Face mirror (`istupakov/parakeet-tdt-0.6b-v3-onnx`) with resume and sha256 verification.

### If voxtype returns empty text or English garbage
Check the microphone level: on some laptops `Internal Mic Boost` = 100% and `Capture` = 100% cause clipping (peak 32768).
The script sets Boost=1, Capture=60% (`amixer -c 0 ...`).
Diagnostics: `arecord -D default -f S16_LE -r 16000 -c 1 -d 5 t.wav && voxtype transcribe t.wav`.

## Omarchy menu translation (`translate-menu.py`)
Omarchy has no i18n, so the script reads the stock menu and writes overrides of `label`/`title` to
`~/.config/omarchy/extensions/omarchy-menu.jsonc`. Entries are written **in full**: Omarchy fills missing fields with empty
values when merging, so a partial override would wipe `action`/`icon`/`when`. The menu reloads when the file is saved.

```mermaid
flowchart LR
    D["/usr/share/omarchy/default/omarchy/omarchy-menu.jsonc"] --> S["translate-menu.py"]
    S -->|"LABELS and TITLES dictionaries"| O["~/.config/omarchy/extensions/omarchy-menu.jsonc"]
    O --> Q["Omarchy menu: full entries with translated label and title"]
```
An existing foreign file is backed up. Run `./translate-menu.py` (idempotent).
New entries added by later Omarchy versions stay in English until added to `LABELS`/`TITLES`.

## Bar panel translation (`translate-plugins.py`)
The translated QML plugins are: calendar (clock), network/Wi-Fi, Bluetooth, audio, power, display, Wi-Fi QR, Speed Test and disk test,
Tailscale, notifications, reminders, clipboard, emojis, image picker; weather is a separate `weather` module.
For each plugin the script:
1. clones it (`omarchy plugin clone`; clones live in `~/.config/omarchy/plugins/<user>.<name>`, are listed as "My …",
   and the originals get disabled);
2. replaces exact string literals from the `TRANSLATIONS` dictionary. Literals in comparisons
   (`===`, `indexOf(`, etc.) and internal keys (DHCP/Custom…) are left alone;
3. applies targeted code edits from `PATCHES` where text is not a literal: the calendar is formatted with the Russian
   locale explicitly (`Qt.locale("ru_RU")`; the plugin forces English by default), and power profile names
   ("Экономия/Баланс/Мощность") are built from system names;
4. restarts the shell (`omarchy restart shell`; without it open panels keep the old code; the bar disappears for a few seconds).

```mermaid
flowchart TD
    A["For each plugin: clock, network, bluetooth, audio, power, monitor, wifiqr"] --> B{"Clone exists?"}
    B -->|no| C["omarchy plugin clone omarchy.name"]
    B -->|yes| D
    C --> D["Replace string literals (TRANSLATIONS), except comparisons"]
    D --> E["Targeted code edits (PATCHES)"]
    E --> F["omarchy restart shell"]
```

The script is idempotent. If a `PATCHES` fragment is not found (the plugin changed upstream), it writes a message to stderr.
**Downside of clones:** they do not receive upstream plugin updates. After `omarchy update`, if a panel breaks or you want the
fresh version: `rm -r ~/.config/omarchy/plugins/$USER.<name>` and run `./translate-plugins.py`
(to get the original back: `omarchy plugin enable omarchy.<name>`).
Not translated: Dropbox, Agents, bar widgets (indicators etc.), emoji names, lock screen and polkit (see "Deliberately not included").
Add new plugins to `TRANSLATIONS` the same way.

## Russian Ministry root certificates (`install-mincifry-ca.sh`)
Needed for Russian government sites and some banks. The script downloads Russian Trusted Root/Sub CA from gu-st.ru, checks
pinned SHA-256 fingerprints (aborts on mismatch) and installs them into the system store (`update-ca-trust`, needs sudo),
the Chromium-family NSS database (`~/.pki/nssdb`), and enables `security.enterprise_roots.enabled` in Firefox profiles.
Restart browsers afterwards.

| Command | Action |
|---------|--------|
| `./install-mincifry-ca.sh` | install (idempotent) |
| `./install-mincifry-ca.sh --remove` | remove from all stores |
| `./install-mincifry-ca.sh --check` | no-sudo check: fingerprints on gu-st.ru and expiry (< 90 days warns) |
| `./install-mincifry-ca.sh --enable-timer` / `--disable-timer` | weekly automatic check (systemd user timer `mincifry-ca-check.timer`) |

```mermaid
flowchart TD
    T["systemd timer: weekly"] --> K["install-mincifry-ca.sh --check"]
    K --> F{"Fingerprint on gu-st.ru matches the pinned one?"}
    F -->|no| N["Notification: certificate changed"]
    F -->|yes| X{"More than 90 days until expiry?"}
    X -->|no| N2["Notification: expiring soon"]
    X -->|yes| OK["Do nothing"]
    N --> H["You: verify at gosuslugi.ru/crt, update SHA256, rerun the installer"]
    N2 --> H
```

There is **deliberately no automatic installation** of new certificates: this is trust in a root authority, so on a fingerprint
change or expiry < 90 days you get a notification and the decision is yours: verify at gosuslugi.ru/crt, update the
`SHA256` values in the script and run it. Expiry: Sub CA 2027-03-06, Root CA 2032-02-27.
Kept separate from `install.sh` on purpose.

## License
MIT, see [LICENSE](LICENSE).
