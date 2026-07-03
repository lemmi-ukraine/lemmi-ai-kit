#!/usr/bin/env sh
# Install the lemmi-ai-kit CLI as a uv tool.
#
#   curl -LsSf https://raw.githubusercontent.com/Reidond/lemmi-ai-kit/main/install.sh | sh
#
# Environment overrides:
#   LEMMI_AI_KIT_REPO  git URL of the kit repo (default below; use git@github.com:... for SSH access to the private repo)
#   LEMMI_AI_KIT_REF   git ref to install (default: latest stable v* tag; falls back to main)
set -eu

REPO="${LEMMI_AI_KIT_REPO:-https://github.com/Reidond/lemmi-ai-kit}"
REF="${LEMMI_AI_KIT_REF:-}"

if ! command -v uv >/dev/null 2>&1; then
  echo "==> Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi

if [ -z "$REF" ]; then
  echo "==> Resolving latest stable release"
  REF="$(git ls-remote --tags --refs "$REPO" 'v*' 2>/dev/null \
    | awk -F/ '{print $NF}' \
    | grep -v -- '-preview\.' \
    | sort -V \
    | tail -n 1 || true)"
fi
if [ -z "$REF" ]; then
  echo "==> No stable release found; installing from main"
  REF="main"
fi

echo "==> Installing lemmi-ai-kit @ ${REF}"
uv tool install --force "git+${REPO}@${REF}"

echo "==> Installed:"
uv tool run --from lemmi-ai-kit lemmi-ai-kit --version 2>/dev/null || lemmi-ai-kit --version

cat <<'EOF'

Next steps — inside your project directory:
  lemmi-ai-kit install            # default profiles (core, skill-authoring, prompts, research, python)
  lemmi-ai-kit install --all      # everything, including extras
  lemmi-ai-kit list               # see what ships
EOF
