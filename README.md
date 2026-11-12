# Setu — Windows PC host + Android remote

Setu is a prototype for viewing and controlling a Windows PC from an Android phone, including when they are on different networks. It consists of a visible Windows host and a native Android app. Both devices must use **Tailscale**, which provides the encrypted private network; there is no Setu cloud relay or account server. The PC must be on, signed in, awake, and running the host.

## Install and connect

1. Install [Tailscale](https://tailscale.com/download) on the Windows PC and Android phone. Sign both in to the same tailnet (or otherwise grant the phone access to the PC), and make sure Tailscale is connected on both. Your tailnet policies must allow connections from the phone to TCP port 8000 on the PC.
2. Install **SetuHostSetup.exe** on the PC and open **Setu PC Host**. Click **Start sharing**. If Windows Firewall asks, allow the connection for the appropriate private network. The host binds only to the PC's Tailscale IPv4, not all interfaces. Keep the window open.
3. Install the **Setu Remote** APK on Android. If Android asks, permit installation from your chosen source. Open it, enter the Tailscale address and access key shown on the PC, and tap **Connect to PC**.
4. Tap the screen to click, hold to right-click, swipe vertically to scroll, or use **Keyboard** and **Keys**. Stop sharing on the PC or disconnect in the app when finished. A fresh random key is generated every time sharing starts.

**These binaries are not checked into the repository.** The GitHub Actions workflow `.github/workflows/build-apps.yml` can build an installer and a debug APK; after running it, download the `Setu-Windows-installer` and `Setu-Android-debug` artifacts from that run. The Windows installer is unsigned and the APK uses a debug signing key; OS security warnings are expected. Inspect and build the code yourself before installing. No release or artifact is implied until the workflow has actually succeeded.

### Build on Windows

Install Python 3.10–3.12 and Inno Setup 6, then from PowerShell at the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File windows/build.ps1
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" windows/installer.iss
```

The installer is at `dist/installer/SetuHostSetup.exe`. Or run `dist/SetuHost/SetuHost.exe` directly, keeping the whole folder together. To run from source instead, install `requirements.txt` and run `python windows/host.py`.

### Build Android

Open `android/` in Android Studio with JDK 17 and Android SDK 35, let Gradle sync, and select **Build > Build APK(s)**. Alternatively run Gradle 8.9 in `android/`: `gradle assembleDebug`. Output: `app/build/outputs/apk/debug/app-debug.apk`. Android 8.0+ is required.

## Safety and limitations

- The Windows host explicitly starts and stops sharing; it does **not** install a background service, automatically start after reboot, bypass the Windows lock screen or UAC, or work while the PC sleeps. Leave the host visible to the PC user. Only use it on computers you own or have permission to control.
- Setu itself uses HTTP, **not TLS**. The Android app restricts addresses to Tailscale IPv4 addresses and the Windows GUI binds to the PC's Tailscale address. Privacy relies on a correctly connected, trusted Tailscale VPN and tailnet access rules; do not port-forward or expose the server to the public internet. A Tailscale address alone is not proof of a VPN connection. Both devices need internet access, with Tailscale connected throughout.
- This is not security-audited. Anyone with network access to the host and the access key can control the logged-in desktop. Keep the key private, limit tailnet access, and stop sharing when finished. Screen updates use JPEG polling, not video streaming. Audio, drag, clipboard, multi-monitor selection and mobile file transfer are not implemented. Text input is ASCII only. Windows display scaling and some applications may affect input; test before relying on it.
- The PC host contains the older browser interface and shared-folder APIs as well; authorized network clients can access files from `Documents/Setu/shared`. The Android app currently does not expose file transfer. Use only with trusted devices and do not store sensitive data in that shared folder.

## Browser demo and tests

`python -m setu.server --demo` runs the older simulated browser desktop (key `demo`); it does not control your computer. The CLI server listens on all interfaces by default and is **not** the Windows GUI host; don't expose it publicly.

```sh
pip install -r requirements.txt pytest httpx
python -m pytest
```
