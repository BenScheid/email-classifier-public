#!/usr/bin/env bash
set -euo pipefail

# Email Classifier setup script
# - Creates a virtual environment
# - Installs Python dependencies
# - Creates local config/model folders
# - Optionally copies Gmail OAuth credentials
# - Optionally switches the active classifier pipeline in src/main.py
# - Optionally starts the app

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
VENV_DIR="$REPO_DIR/.venv"
CONFIG_DIR="$REPO_DIR/.configs"
MODELS_DIR="$REPO_DIR/models"
MAIN_FILE="$REPO_DIR/src/main.py"
REQUIREMENTS_FILE="$REPO_DIR/requirements.txt"
CONFIG_FILE="$REPO_DIR/config.json"
CREDENTIALS_DEST="$CONFIG_DIR/credentials.json"

PIPELINE="embeddings"
RUN_APP=0
CREDENTIALS_SOURCE=""
PYTHON_BIN=""

usage() {
  cat <<'EOF'
Usage:
  bash setup_email_classifier.sh [options]

Options:
  --credentials PATH      Copy Gmail OAuth credentials.json from PATH
  --pipeline NAME         Select active pipeline: embeddings or nli
  --run                   Start the app after setup
  --python BIN            Python binary to use (default: python3, then python)
  -h, --help              Show this help text

Examples:
  bash setup_email_classifier.sh
  bash setup_email_classifier.sh --credentials ~/Downloads/credentials.json
  bash setup_email_classifier.sh --pipeline nli
  bash setup_email_classifier.sh --credentials ~/Downloads/credentials.json --pipeline embeddings --run
EOF
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
  printf '\nError: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --credentials)
      [[ $# -ge 2 ]] || fail "--credentials requires a file path"
      CREDENTIALS_SOURCE="$2"
      shift 2
      ;;
    --pipeline)
      [[ $# -ge 2 ]] || fail "--pipeline requires 'embeddings' or 'nli'"
      PIPELINE="$2"
      shift 2
      ;;
    --run)
      RUN_APP=1
      shift
      ;;
    --python)
      [[ $# -ge 2 ]] || fail "--python requires a binary name or path"
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

if [[ "$PIPELINE" != "embeddings" && "$PIPELINE" != "nli" ]]; then
  fail "Invalid pipeline '$PIPELINE'. Use 'embeddings' or 'nli'."
fi

if [[ ! -f "$MAIN_FILE" || ! -f "$REQUIREMENTS_FILE" || ! -f "$CONFIG_FILE" ]]; then
  fail "This script must be placed in the project root, next to src/, requirements.txt, and config.json."
fi

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    fail "Python was not found. Install Python 3.10+ and try again."
  fi
fi

log "Using Python: $PYTHON_BIN"
cd "$REPO_DIR"

log "Creating local folders"
mkdir -p "$CONFIG_DIR" "$MODELS_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating virtual environment in $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  log "Virtual environment already exists"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Upgrading pip"
python -m pip install --upgrade pip

log "Installing dependencies"
pip install -r "$REQUIREMENTS_FILE"

if [[ -n "$CREDENTIALS_SOURCE" ]]; then
  [[ -f "$CREDENTIALS_SOURCE" ]] || fail "Credentials file not found: $CREDENTIALS_SOURCE"
  log "Copying Gmail OAuth credentials to $CREDENTIALS_DEST"
  cp "$CREDENTIALS_SOURCE" "$CREDENTIALS_DEST"
fi

if [[ ! -f "$CREDENTIALS_DEST" ]]; then
  cat <<EOF

[notice] Gmail credentials are not set up yet.
Place your OAuth desktop credentials file here before running the app:
  $CREDENTIALS_DEST
EOF
else
  log "Gmail credentials found"
fi

log "Setting active pipeline to '$PIPELINE' in src/main.py"
python - <<'PY'
from pathlib import Path
import os, re, sys

main_file = Path(os.environ['MAIN_FILE'])
pipeline = os.environ['PIPELINE']
text = main_file.read_text(encoding='utf-8')

embedding_block = "run_embeddings()"
nli_block = "run_nli()"

if pipeline == 'embeddings':
    text = re.sub(r'^\s*#?\s*run_embeddings\(\)\s*$', 'run_embeddings()', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*#?\s*run_nli\(\)\s*$', '# run_nli()', text, flags=re.MULTILINE)
else:
    text = re.sub(r'^\s*#?\s*run_embeddings\(\)\s*$', '# run_embeddings()', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*#?\s*run_nli\(\)\s*$', 'run_nli()', text, flags=re.MULTILINE)

main_file.write_text(text, encoding='utf-8')
print(f"Active pipeline set to: {pipeline}")
PY

cat <<EOF

Setup complete.

Project root:      $REPO_DIR
Virtual env:       $VENV_DIR
Config folder:     $CONFIG_DIR
Models folder:     $MODELS_DIR
Active pipeline:   $PIPELINE

Next steps:
1. Make sure Gmail OAuth credentials exist at:
   $CREDENTIALS_DEST
2. Edit config.json if you want to change categories.
3. Run the project with:
   source "$VENV_DIR/bin/activate"
   python src/main.py
EOF

if [[ "$RUN_APP" -eq 1 ]]; then
  if [[ ! -f "$CREDENTIALS_DEST" ]]; then
    fail "Cannot start the app because credentials.json is missing."
  fi
  log "Starting the app"
  python src/main.py
fi
