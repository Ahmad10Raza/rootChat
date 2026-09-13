# 🚀 Publishing rootChat to Flathub: Complete Step-by-Step Guide

This guide provides the complete, authoritative documentation for publishing **rootChat** to [Flathub](https://flathub.org) ([github.com/flathub/flathub](https://github.com/flathub/flathub)), the premier app store and repository for Linux desktop applications.

---

## 1. Application Identity & Architecture

| Parameter | Value |
|---|---|
| **Application ID (RDNN)** | `io.github.Ahmad10Raza.rootChat` |
| **GitHub Upstream Repo** | `https://github.com/Ahmad10Raza/rootChat` |
| **Current Target Release** | `v0.7.1` |
| **Flatpak Runtime** | `org.kde.Platform` (branch `6.10`) |
| **Flatpak BaseApp** | `io.qt.PySide.BaseApp` (branch `6.10`, provides native Qt 6 & PySide6) |
| **Target Architectures** | `x86_64` and `aarch64` |
| **Publisher Verification** | Automatic "Verified" badge on Flathub via `@Ahmad10Raza` GitHub ownership |

### Sandboxing & Security Permissions

rootChat runs strictly within the Flatpak sandbox with minimal necessary capabilities:
- `--share=network`: Required to connect to the local Ollama daemon (`http://localhost:11434`) and remote LAN inference endpoints.
- `--socket=wayland` & `--socket=fallback-x11`: Native display server integration for Wayland and X11 sessions.
- `--device=dri`: Direct Rendering Infrastructure (hardware acceleration for Qt GUI).
- `--socket=pulseaudio`: Audio notification alerts.
- `--talk-name=org.freedesktop.Notifications`: FreeDesktop desktop notification popups upon response completion.
- `--talk-name=org.kde.StatusNotifierWatcher`: Linux system tray integration.
- `--filesystem=xdg-documents:ro`: Read-only access to user Documents for Knowledge Base document ingestion.

---

## 2. ⚠️ Critical Flathub Policy: Generative AI Policy

Flathub has an explicit [Generative AI Policy](https://docs.flathub.org/docs/for-app-authors/requirements#generative-ai-policy) that submitters must follow:

> *"AI tools or agents must not open or automate Flathub submission pull requests, or generate their commit messages, descriptions, review comments, or replies. Submitters must not request AI-agent reviews."*

### What this means for you:
1. **You (Ahmad10Raza) must submit the PR yourself** directly from your personal GitHub account. Do not use an AI bot or automated script to open the pull request against `flathub/flathub`.
2. **You must include a disclosure in the PR checklist**: All packaging files, metainfo, and manifests in `packaging/flatpak/` have been pre-validated and formatted for you. Below in Section 4 is the exact disclosure statement to copy into your PR.

---

## 3. Pre-Flight Verification & Included Assets

All required Flatpak submission files have been prepared and validated in `packaging/flatpak/`:

```
packaging/flatpak/
├── io.github.Ahmad10Raza.rootChat.yaml         # Flatpak build manifest
├── python3-dependencies.json                 # Pinned offline Python wheels (requests, pymupdf, docx)
├── io.github.Ahmad10Raza.rootChat.desktop     # XDG Desktop entry
├── io.github.Ahmad10Raza.rootChat.metainfo.xml# AppStream metainfo specification
└── rootChat.sh                               # Flatpak startup launcher
```

### Local Verification Checks
You can verify the assets at any time using local tools:

```bash
# 1. Validate AppStream Metainfo
appstreamcli validate --no-net --pedantic resources/metainfo/io.github.Ahmad10Raza.rootChat.metainfo.xml

# 2. Validate Desktop Entry
desktop-file-validate resources/desktop/io.github.Ahmad10Raza.rootChat.desktop

# 3. Validate Manifest Syntax
python3 -c "import yaml; yaml.safe_load(open('packaging/flatpak/io.github.Ahmad10Raza.rootChat.yaml'))"
python3 -m json.tool packaging/flatpak/python3-dependencies.json > /dev/null
```

---

## 4. Step-by-Step Submission Instructions

Follow these exact steps to submit `rootChat` to Flathub:

### Step 1: Fork the Flathub Repository
1. Navigate to: **[https://github.com/flathub/flathub](https://github.com/flathub/flathub)**
2. Click the **Fork** button (top right).
3. ⚠️ **IMPORTANT**: In the fork dialog, **UNCHECK** the checkbox labeled *"Copy the master branch only"*. Flathub requires the `new-pr` branch!
4. Click **Create Fork**.

### Step 2: Clone your Fork and Checkout `new-pr`
In your terminal on your workstation:

```bash
# Navigate to a temporary workspace or your projects folder
cd ~/Documents/TutorialHaven

# Clone your flathub fork
git clone https://github.com/Ahmad10Raza/flathub.git flathub-submission
cd flathub-submission

# Checkout the required new-pr branch
git checkout --track origin/new-pr

# Create a new topic branch for the submission
git checkout -b add-rootchat new-pr
```

### Step 3: Copy the Packaging Files into the Root of the Branch
Copy the 5 prepared files from `rootChat/packaging/flatpak/` directly into the root of your `flathub-submission` directory:

```bash
# Assuming rootChat is at ../rootChat/rootChat:
cp ../rootChat/rootChat/packaging/flatpak/* .

# Check that the files are in place:
ls -la
# You should see:
# - io.github.Ahmad10Raza.rootChat.yaml
# - python3-dependencies.json
# - io.github.Ahmad10Raza.rootChat.desktop
# - io.github.Ahmad10Raza.rootChat.metainfo.xml
# - rootChat.sh
```

### Step 4: Commit and Push to Your Fork

```bash
git add io.github.Ahmad10Raza.rootChat.yaml python3-dependencies.json io.github.Ahmad10Raza.rootChat.desktop io.github.Ahmad10Raza.rootChat.metainfo.xml rootChat.sh

git commit -m "Add io.github.Ahmad10Raza.rootChat"

git push -u origin add-rootchat
```

### Step 5: Open the Pull Request on GitHub
1. Open your browser and go to your fork:
   `https://github.com/Ahmad10Raza/flathub`
2. Click **Compare & pull request** on the `add-rootchat` branch.
3. ⚠️ **CRITICAL CHECK**: Ensure the base branch dropdown is set to:
   - **base repository**: `flathub/flathub`
   - **base branch**: `new-pr` (NOT `master`)
   - **head repository**: `Ahmad10Raza/flathub`
   - **compare branch**: `add-rootchat`
4. **PR Title**:
   ```
   Add io.github.Ahmad10Raza.rootChat
   ```
5. **PR Description**: Fill out the official Flathub template below:

```markdown
### Please confirm your submission meets all the criteria

- [x] Please describe the application briefly:
rootChat is a private, offline-first local AI desktop assistant for Linux powered exclusively by Ollama. It features persistent long-term memory, document knowledge base (RAG) with local vector retrieval, an in-app model manager, and customizable prompt personas.

- [x] Please attach a video showcasing the application on Linux using the Flatpak:
(Drag-and-drop a short 10-30s screen recording or GIF of rootChat running on your Linux desktop into this box)

- [x] The Flatpak ID follows all the rules listed in the Application ID requirements.

- [x] I have read and followed all the Submission requirements and the Submission guide and I agree to them.

- [x] The application has a meaningful development history, evidence of real-world use, and a clear commitment to ongoing maintenance, as required by the development history requirements.

- [x] I have disclosed any AI-generated material included in the application or its Flathub packaging, as required by the Generative AI policy.
**Affected parts and approximate extent:**
AI coding assistants were utilized during development for code generation, UI styling, and packaging manifest preparation. All source code, manifests, and documentation have been manually reviewed, tested, modified, and assumed full maintainer responsibility by me.

- [x] I have not used AI tools or agents to generate or automate this submission pull request or its review interactions.

- [x] I am a developer of the project: https://github.com/Ahmad10Raza/rootChat
```

6. Click **Create Pull Request**.

---

## 5. What Happens After Opening the PR

1. **Flathub Test Bot (`@flathubbot`)**:
   - Within minutes, the automated build bot will start building your Flatpak on both `x86_64` and `aarch64`.
   - Once built, the bot will post a comment with a command to test-install the build directly on your machine:
     ```bash
     flatpak install --user https://dl.flathub.org/build-repo/.../io.github.Ahmad10Raza.rootChat.flatpakref
     ```
2. **Flathub Review Team**:
   - A Flathub reviewer will inspect your manifest, sandbox permissions, and metainfo.
   - If they request minor changes (e.g. adjust a category or permission), commit them to your `add-rootchat` branch and push — the PR will update automatically!
3. **Approval & Merging**:
   - Once approved, the reviewer merges the PR into `new-pr`.
   - Flathub automatically creates a dedicated repository:
     `https://github.com/flathub/io.github.Ahmad10Raza.rootChat`
   - You will receive a GitHub invitation to be the owner/maintainer of that repository.
4. **Publication & Verification**:
   - Your app will be published to the Flathub catalog (`flathub.org/apps/io.github.Ahmad10Raza.rootChat`).
   - Because your app ID matches `io.github.Ahmad10Raza.*`, your app will display the official **"Verified" checkmark badge** automatically!

---

## 6. How Future Updates Work

When you release a new version (e.g. `v0.7.2`):
1. Create and publish the GitHub release with git tag `v0.7.2`.
2. Compute the new sha256 checksum:
   ```bash
   curl -sSL https://github.com/Ahmad10Raza/rootChat/archive/refs/tags/v0.7.2.tar.gz | sha256sum
   ```
3. In your `flathub/io.github.Ahmad10Raza.rootChat` repo:
   - Update the URL and sha256 in `io.github.Ahmad10Raza.rootChat.yaml`.
   - Add the `<release>` entry to `io.github.Ahmad10Raza.rootChat.metainfo.xml`.
   - Push to `master`.
4. Flathub's build bots will automatically compile and distribute the update to all Linux users worldwide!
