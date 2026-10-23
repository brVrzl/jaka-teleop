# Right Touch extension for the existing Quest sender

Current priority: validate the prebuilt Trossen Quest APK first. This Unity
build workflow is deferred unless real tests show existing applications cannot
meet the input requirements. See [Mac handoff](../docs/setup/MAC_QUEST_HANDOFF.md).

This directory contains a focused patch for
[`brVrzl/hand-tracking-streamer`](https://github.com/brVrzl/hand-tracking-streamer/tree/5b8eac7e30ce12481b89b123099693bc658bc578),
branch `feature/mixed-input-log-probe`, commit
`5b8eac7e30ce12481b89b123099693bc658bc578`.

It extends the existing `LeftControllerPacketSender` socket owner with an
explicit **Right Touch (RTOUCH v1)** mode. The existing Unity scene, Meta SDK,
IP/port keyboard, start/stop menu, saved configuration and Android build entry
are reused. Hand modes 0–2 retain CTRL v1 and HTS. Mode 3 sends RTOUCH only,
with real right-controller and head poses, and disables HTS hand/head streams.
The existing left menu button remains a stop action; right **B** also stops in
Right Touch mode, so stopping does not require a left controller.

This source is a candidate matching the observed CTRL framing, **not proof of
the installed Quest APK's provenance**. Main has a bundled APK, but this
feature branch has no APK and there are no GitHub Releases. Do not install the
main APK as if it contained this extension.

## Rebuild on a Unity build computer

The pinned source requires **Unity 6000.0.65f1**, Meta All-in-One SDK **72.0.0**,
OpenXR **1.16.1**, Input System **1.17.0**, Android Build Support, SDK/NDK and
OpenJDK. Package versions come from that project's manifest/lock, not this
host's Python environment. Complete Unity's own Editor activation requirements.

In a fresh checkout (keep any existing sender checkout and its changes):

```bash
git clone --single-branch --branch feature/mixed-input-log-probe \
  https://github.com/brVrzl/hand-tracking-streamer.git hand-tracking-streamer-right-touch
cd hand-tracking-streamer-right-touch
git switch -c work/right-touch-v1 5b8eac7e30ce12481b89b123099693bc658bc578
git apply --check /absolute/path/to/embodied-hand-lab/quest_sender/right-touch-v1.patch
git apply /absolute/path/to/embodied-hand-lab/quest_sender/right-touch-v1.patch
```

Open `hand_tracking_streamer/` in Unity Hub once, let the pinned packages
resolve, and inspect Project Validation without upgrading packages. Then run
on Linux/macOS (Windows can call the same Editor flags or open the project):

```bash
export UNITY_EDITOR=/absolute/path/to/Unity
export SENDER_PROJECT="$PWD/hand_tracking_streamer"
mkdir -p "$SENDER_PROJECT/build"
"$UNITY_EDITOR" -batchmode -projectPath "$SENDER_PROJECT" -runTests \
  -testPlatform EditMode -testResults "$SENDER_PROJECT/build/editmode.xml" \
  -logFile "$SENDER_PROJECT/build/editmode.log"
"$UNITY_EDITOR" -batchmode -quit -buildTarget Android -projectPath "$SENDER_PROJECT" \
  -executeMethod CommandLineAndroidBuild.BuildApk \
  -apkOutput "$SENDER_PROJECT/build/right_touch_v1.apk" \
  -logFile "$SENDER_PROJECT/build/build.log"
```

The patch assigns a distinct package
`com.brvrzl.handtrackingstreamer.righttouch` and version
`1.1.0-righttouch-v1`, preserving the installed legacy application's package.
Keep APK/build logs outside Git. The main repository's
[Right Touch guide](../docs/motion_input/RIGHT_TOUCH.md) covers installation,
menu settings, input preview and simulation.

## Validation status

The patch was applied and reverse-checked against the seven affected source
files downloaded from the pinned commit. Host protocol/safety tests and a
121-frame synthetic MuJoCo replay passed; they do not validate the Android app.
Thor currently has no Unity Editor. **The patched sender has not been compiled,
installed, or tested on Quest.** Preserve actual EditMode/build logs and verify
head/controller tracking, focus/pause/recenter session changes, UI start/stop,
IP/port edits, packet receipt and app identity before claiming end-to-end use.

The patch uses [Meta SDK 72 OVRInput](https://developers.meta.com/vr/reference/unity/v72/class_o_v_r_input/)
for controller position/orientation tracking and local grip pose, transforms it
through the existing `OVRCameraRig.trackingSpace`, and uses the real center-eye
anchor in the same Unity world. The host performs the sole Unity-to-OpenXR
basis conversion. Focus/pause and XR tracking-origin events change the session;
network restart also starts a new session. Neither reconnect nor holding Grip
across interruption authorizes host motion.
