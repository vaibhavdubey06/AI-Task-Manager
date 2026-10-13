# ✅ Pre-Flight Recording & Verification Checklist

**Project**: Autonomous AI Task Worker  
**Goal**: Flawless, professional 3-minute screen and audio capture for CentrAlign AI technical evaluation.

---

## 1. Environment & Application Startup

- [ ] **Python Virtual Environment Activated**:
  ```powershell
  cd c:\Users\dubey\OneDrive\Desktop\AI_Task_Manager
  .\.venv\Scripts\activate
  ```
- [ ] **Streamlit Application Running**:
  ```powershell
  streamlit run app.py --server.port 8501
  ```
- [ ] **Automated Tests Passing (Sanity Check)**:
  ```powershell
  pytest -v
  ```
  *(Verify that all 24 tests pass before starting your recording).*

---

## 2. API Configuration & LLM Mode Confirmation

- [ ] **`.env` File Loaded**:
  Ensure `.env` contains your active provider credentials:
  ```ini
  OPENAI_BASE_URL=https://api.groq.com/openai/v1
  OPENAI_API_KEY=gsk_...
  OPENAI_MODEL=openai/gpt-oss-120b
  ```
- [ ] **Execution Intelligence Mode Confirmed in UI**:
  - Open `http://localhost:8501`.
  - Look at the sidebar top card:
    - If using live API: Displays `Mode: 🟢 LLM Planning Enabled` and the active model name.
    - If testing offline fallback: Displays `Mode: 🟡 Deterministic Fallback` with explicit reason (`OPENAI_API_KEY / GROQ_API_KEY unavailable`).
  - *Rule*: Never claim live LLM planning if your screen shows Deterministic Fallback. Disclose the mode truthfully.
- [ ] **Security Verification**:
  Ensure your `.env` file, API keys, and terminal windows containing secrets are **never visible on screen**.

---

## 3. Data & Environment Seeding

- [ ] **Sample Invoices Present in `data/invoices/`**:
  Verify the five fixture invoices exist:
  - `INV-2024-001_Acme_Technologies.json`
  - `INV-2024-002_Acme_Technologies.txt` (Latest Acme invoice: $2,750.50 due 2024-10-31)
  - `INV-2024-003_Apex_Global.json`
  - `INV-2024-004_Corrupted_Invoice.json`
  - `INV-2024-005_Ambiguous_Vendor.txt` (Ambiguity test: Joint venture billing without specific due date)
- [ ] **Database Reset Executed**:
  - In the sidebar under **Demo Controls**, click **`🔄 Reset Demo Environment`**.
  - Confirm the toast: `Database wiped clean!`.
  - Confirm `SQLite Accounts Payable` table shows: *No payable records in SQLite database yet.*

---

## 4. Test Run Dry-Run (Rehearsal)

- [ ] **Dry-Run 1: Flagship Acme Workflow**:
  - Click preset `📌 Acme Tech (Latest)`.
  - Click `🚀 Execute Autonomous Worker`.
  - Confirm pause at `### ⚠️ Human-in-the-Loop Approval Required` ($2,750.50 due 2024-10-31).
  - Click `✅ Approve & Commit to Accounts Payable`.
  - Confirm status transitions to `✅ Task Completed & Verified` (`SUCCESSFUL`).
  - Confirm all four checkmarks render `✅ MATCH` in the **Independent Verification Evidence** card.
  - Reset environment again after rehearsal.
- [ ] **Dry-Run 2: Ambiguous Vendor Clarification**:
  - Click preset `❓ Ambiguous Vendor`.
  - Click `🚀 Execute Autonomous Worker`.
  - Confirm pause at `### ❓ User Clarification Required`.
  - Type `Process Acme Technologies` into the clarification input box.
  - Click `🚀 Submit Clarification & Resume Task`.
  - Confirm task resumes and completes.
  - Reset environment again before recording take 1.

---

## 5. Screen Capture & Display Settings

- [ ] **Browser Window Setup**:
  - Use Chrome or Edge in **clean window mode** (F11 fullscreen or a dedicated desktop space).
  - Close all other browser tabs, bookmarks bars, and personal extensions.
  - **Browser Zoom Level**: Set to **110% or 125%** so all text, code snippets, and metrics are razor-sharp on laptop and mobile screens.
- [ ] **Operating System Hygiene**:
  - Enable **Focus Assist / Do Not Disturb** on Windows (`Win + N` -> Focus).
  - Mute notifications from Slack, Discord, WhatsApp, Email, and Calendar alerts.
  - Hide desktop clutter and taskbar badges if recording full desktop.
- [ ] **Screen Resolution**:
  - Target recording resolution: **1080p (1920x1080)** or **1440p (2560x1440)** at 30 or 60 fps.

---

## 6. Audio Setup & Voiceover Check

- [ ] **Microphone Selection**:
  - Ensure your recording software (Loom, OBS, or Windows Xbox Game Bar `Win + Alt + R`) selects your primary headset or dedicated USB microphone, not the internal laptop mic.
- [ ] **Audio Gain & Noise Floor**:
  - Record a 10-second audio sample speaking at your normal presentation volume.
  - Check for fan noise, air conditioner hum, or room echo.
  - Ensure speech volume peaks around -6 dB to -3 dB without digital clipping (distortion).
- [ ] **Separate Audio Track Strategy (Recommended)**:
  - If recording voiceover separately after screen capture:
    1. Record the screen actions following the exact timing in `VIDEO_VOICEOVER_SCRIPT.md`.
    2. Import the video into your editor (CapCut, Premiere, DaVinci Resolve, or Loom).
    3. Read `VOICEOVER_ONLY.md` while watching the screen playback.

---

## 7. Post-Capture Review Checklist

- [ ] **Total Video Length**: Between **2:50 and 3:10** (strictly under 3:15).
- [ ] **Pacing Check**: Speech is unhurried and clear; user interface interactions match the spoken words.
- [ ] **Visual Clarity Check**: All text, badges, and verification results (`MATCH`) are legible.
- [ ] **Audio Clarity Check**: Voice is crisp, consistent in volume, and free of background clicks or heavy breathing.
- [ ] **Zero Secret Leaks**: Verified that no API keys, IP addresses, or personal folders appeared in the recording.
- [ ] **Upload & Deliverable**:
  - Export MP4 at H.264 / AAC.
  - Upload unlisted to Loom or YouTube, or upload directly to Google Drive with link sharing set to *Anyone with the link can view*.
