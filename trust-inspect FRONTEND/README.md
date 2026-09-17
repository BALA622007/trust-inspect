# TRUST INSPECT — Mobile App

Smart Real-Time Monitoring & Inspection — SIH prototype (inspector-side Flutter app).

This zip contains:
- `lib/main.dart` — full stabilized app code
- `pubspec.yaml` — minimal Flutter project config
- This `README.md`

> **Note:** Only `lib/main.dart` and `pubspec.yaml` are included here. To actually run the app you still need the standard Flutter project scaffolding folders (`android/`, `ios/`, etc.). If you already have an existing `trust_inspect_mobile` Flutter project, just copy `lib/main.dart` into your project's `lib/` folder, replacing the old one. If you don't have a project yet, see Section 3 below.

---

## 1. Architecture

### Trust loop (overall system concept)

```
DATA → AI FUSION → EXPLANATION → DECISION → ACTION → HUMAN REVIEW → VERIFIED OUTCOME → MODEL FEEDBACK
```

### This app's structure (`lib/main.dart`)

- `TrustInspectApp` — app root, starts at `LoginPage`
- `LoginPage` — local demo login only (`inspector` / `1234`). **Not connected to any backend.**
- `DashboardPage` — shows demo stats and a demo "today's inspections" list, with bottom navigation (Home / Inspections / Profile). Profile opens `AlertMembersPage`.
- `ProjectRiskPage` — shows a demo project's risk score, AI risk factors, recommendation, confidence, a placeholder `START INSPECTION` button, and a working `SEND ALERT` button that opens a recipient-selection dialog.
- `AlertMembersPage` — manage the list of officers who can receive alerts. Starts empty. Add/delete supported. Deleting a member notifies the other configured members first (as a demo message).
- `AddAlertMemberPage` — form to add a new alert member (name, role, email, phone), with validation and a 10-digit numeric-only phone field.

The alert-member list (`alertMembers`) is a single shared in-memory list declared once, above `main()`, so every page reads/writes the same list.

### What is real vs. demo in this build

- Login: demo only, hardcoded credentials, not connected to a backend.
- Dashboard stats and inspection cards: hardcoded demo values.
- Project risk score, anomalies, and confidence: hardcoded demo values for one sample project.
- Alert members: real in-app state (add/delete/list actually works and persists for the app session), but **not saved to any backend** — it resets when the app restarts.
- Sending an alert: the recipient selection actually works, but no real SMS/email/WhatsApp provider is connected. No one actually receives a message yet — this is UI/demo only, clearly labeled in the code and in on-screen messages.

None of the above should be presented as a finished, backend-connected, or real-notification feature until those parts are actually built.

---

## 2. How to run

### Option A — you already have a Flutter project set up

1. Copy `lib/main.dart` from this zip into your existing project's `lib/` folder (replace the old file).
2. Open your project folder in VS Code (`File → Open Folder`, select the folder that has `android`, `ios`, `lib`, `pubspec.yaml` — not the `lib` folder itself).
3. Open a terminal in that project folder and run:
   ```powershell
   flutter pub get
   flutter run
   ```
   To target one specific connected device:
   ```powershell
   flutter devices
   flutter run -d <device-id>
   ```
4. While `flutter run` is active in that terminal, you can press:
   - `r` — hot reload
   - `R` — hot restart
   - `q` — quit
   (These only work while `flutter run` is running, not at a normal terminal prompt.)

### Option B — starting a brand new Flutter project

1. Create a new Flutter project:
   ```powershell
   flutter create trust_inspect_mobile
   cd trust_inspect_mobile
   ```
2. Replace the generated `lib/main.dart` with the one from this zip.
3. Replace the generated `pubspec.yaml`'s `dependencies`/`flutter` sections with the ones from this zip's `pubspec.yaml` (or just merge in `cupertino_icons` if not already there).
4. Run:
   ```powershell
   flutter pub get
   flutter run
   ```

---

## 3. Known limitations / next steps

- Backend integration for alert members (create/list/update/delete) is not implemented yet.
- Real notification provider (SMS/email) is not connected — sending an alert is a UI action only.
- Audit/ledger entries for alert actions are not implemented yet.
- `START INSPECTION` is a placeholder; the full inspection workflow (GPS, evidence capture, checklist, submission) is not implemented yet.
- Login is not connected to the backend (backend currently has no login endpoint).
