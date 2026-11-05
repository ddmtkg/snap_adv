# Snap Adv 0.1.1 for Windows x64

1. Extract the download ZIP.
2. Run `snap_0.1.1_x64-setup.exe` and complete installation.
3. Start **snap** from the Start menu if it did not launch at the end of setup.
4. Snap runs in the notification area; it does not open a normal main window.
5. Press **Ctrl+Shift+S**. Capture currently uses your **primary monitor**.
6. Drag to select a region, then use **R** for a rectangle, **A** for an arrow,
   or **T**, click, type your comment, and Enter to finish the comment.
7. Press **Enter** again to save. **Esc** cancels the capture.
8. Find the matching PNG and JSON files in `%USERPROFILE%\.snap\inbox`.
   You can ZIP several pairs together and send them to your AI assistant.

The tray menu offers **Open Logs** (opens `%USERPROFILE%\.snap`) and **Quit Snap**.
The app does not install MCP integrations or enable sign-in startup by itself.
No Python, Node.js, Rust, or Git installation is needed to use the desktop app.

## Portable alternative

Run `snap-portable.exe` from a folder of your choice. It uses the same inbox.
Run only one copy of Snap at a time. The portable version needs Microsoft Edge
WebView2 Runtime, normally present on Windows 11; the installer can install it
if missing.

## Verification and troubleshooting

This build is unsigned, so Windows may show an Unknown Publisher/SmartScreen
notice. The included `SHA256SUMS.txt` records each EXE's checksum; compare using
`Get-FileHash .\snap_0.1.1_x64-setup.exe -Algorithm SHA256`.

If the hotkey does nothing, quit any other Snap instance and check whether
another program already uses Ctrl+Shift+S. Diagnostic log:
`%USERPROFILE%\.snap\snap.log`.

Automated Windows CI installs this EXE and exercises tray launch, the global
hotkey, crop, rectangle/text annotation, saving PNG + JSON, repeated capture,
and Escape cancellation. Multi-monitor setups and different display scaling
still need testing on your own PC.

The original MIT license is included. The full review tracker, AI reply import,
and user-confirmed closing of remarks are planned separately.
