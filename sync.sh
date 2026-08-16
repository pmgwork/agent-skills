#!/usr/bin/env bash
#
# sync.sh - Synchronize agent skills into ~/.agents/skills
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/skills"
TARGET_DIR="${HOME}/.agents/skills"

print_usage() {
    cat <<EOF
Usage: ./sync.sh [options]

Options:
  -s, --status   Show current synchronization status
  -u, --unlink   Remove symlinks pointing to this repository
  -h, --help     Show this help message
EOF
}

show_status() {
    echo "==> Skills Status"
    echo "Source: ${SRC_DIR}"
    echo "Target: ${TARGET_DIR}"
    echo ""
    if [ ! -d "$TARGET_DIR" ]; then
        echo "Target directory does not exist: ${TARGET_DIR}"
        return
    fi
    echo "Skills in repository:"
    for skill in "$SRC_DIR"/*; do
        [ -d "$skill" ] || continue
        name="$(basename "$skill")"
        link="${TARGET_DIR}/${name}"
        if [ -L "$link" ]; then
            dest="$(readlink "$link" || true)"
            if [ "$dest" = "$skill" ]; then
                echo "  ✔ ${name}"
            else
                echo "  ⚠ ${name} (points to ${dest})"
            fi
        elif [ -e "$link" ]; then
            echo "  ⚠ ${name} (exists as file/dir)"
        else
            echo "  ✖ ${name} (not linked)"
        fi
    done
}

unlink_skills() {
    echo "==> Unlinking skills from ${TARGET_DIR}"
    local count=0
    for link in "$TARGET_DIR"/*; do
        [ -L "$link" ] || continue
        dest="$(readlink "$link" || true)"
        if [[ "$dest" == "$SRC_DIR"/* ]]; then
            rm "$link"
            echo "  ✔ Removed: $(basename "$link")"
            count=$((count + 1))
        fi
    done
    echo "Unlinked ${count} skill(s)."
}

sync_skills() {
    echo "==> Synchronizing skills to ${TARGET_DIR}"
    mkdir -p "$TARGET_DIR"

    # 1. Create or update symlinks
    for skill in "$SRC_DIR"/*; do
        [ -d "$skill" ] || continue
        name="$(basename "$skill")"
        link="${TARGET_DIR}/${name}"
        ln -sfn "$skill" "$link"
        echo "  ✔ ${name}"
    done

    # 2. Clean up broken/orphan links
    for link in "$TARGET_DIR"/*; do
        [ -L "$link" ] || continue
        dest="$(readlink "$link" || true)"
        if [[ "$dest" == "$SRC_DIR"/* ]] && [ ! -e "$dest" ]; then
            rm "$link"
            echo "  ✖ Removed orphan: $(basename "$link")"
        fi
    done

    # 3. Ensure agent aliases
    for alias in "${HOME}/.gemini/skills" "${HOME}/.claude/skills"; do
        parent="$(dirname "$alias")"
        if [ -d "$parent" ] && [ ! -e "$alias" ]; then
            ln -sfn "$TARGET_DIR" "$alias"
            echo "  ✔ Alias created: ${alias} -> ${TARGET_DIR}"
        fi
    done

    echo "==> Done!"
}

case "${1:-}" in
    -s|--status)
        show_status
        ;;
    -u|--unlink)
        unlink_skills
        ;;
    -h|--help)
        print_usage
        ;;
    "")
        sync_skills
        ;;
    *)
        echo "Unknown option: $1" >&2
        print_usage
        exit 1
        ;;
esac
