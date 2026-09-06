#!/usr/bin/env bash
#
# sync.sh - Synchronize agent skills into ~/.agents/skills
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/skills"
TARGET_DIR="${HOME}/.agents/skills"
DRY_RUN=false
CUSTOM_TARGET=false
MODE=sync

print_usage() {
    cat <<EOF
Usage: ./sync.sh [options]

Options:
  -t, --target DIR  Synchronize only to DIR (no agent aliases)
      --dry-run     Preview changes without writing
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
            if ! $DRY_RUN; then rm "$link"; fi
            echo "  ✔ Removed: $(basename "$link")"
            count=$((count + 1))
        fi
    done
    echo "Unlinked ${count} skill(s)."
}

sync_skills() {
    echo "==> Synchronizing skills to ${TARGET_DIR}"
    if ! $DRY_RUN; then mkdir -p "$TARGET_DIR"; fi
    local conflicts=0

    # 1. Create missing symlinks and preserve conflicts
    for skill in "$SRC_DIR"/*; do
        [ -d "$skill" ] || continue
        name="$(basename "$skill")"
        link="${TARGET_DIR}/${name}"
        if [ -L "$link" ] && [ "$(readlink "$link")" = "$skill" ]; then
            echo "  ✔ ${name} (already linked)"
        elif [ -e "$link" ] || [ -L "$link" ]; then
            echo "  ⚠ Conflict preserved: ${link}" >&2
            conflicts=$((conflicts + 1))
        else
            if ! $DRY_RUN; then ln -s "$skill" "$link"; fi
            echo "  + Link: ${name}"
        fi
    done

    # 2. Clean up broken/orphan links
    for link in "$TARGET_DIR"/*; do
        [ -L "$link" ] || continue
        dest="$(readlink "$link" || true)"
        if [[ "$dest" == "$SRC_DIR"/* ]] && [ ! -e "$dest" ]; then
            if ! $DRY_RUN; then rm "$link"; fi
            echo "  ✖ Removed orphan: $(basename "$link")"
        fi
    done

    # 3. Ensure agent aliases
    if ! $CUSTOM_TARGET; then
        for alias in "${HOME}/.gemini/skills" "${HOME}/.claude/skills"; do
            parent="$(dirname "$alias")"
            if [ -d "$parent" ] && [ ! -e "$alias" ] && [ ! -L "$alias" ]; then
                if ! $DRY_RUN; then ln -s "$TARGET_DIR" "$alias"; fi
                echo "  ✔ Alias created: ${alias} -> ${TARGET_DIR}"
            fi
        done
    fi
    if [ "$conflicts" -gt 0 ]; then
        echo "==> ${conflicts} conflict(s); existing entries preserved." >&2
        return 1
    fi
    echo "==> Done!"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -s|--status|-u|--unlink)
            if [ "$MODE" != sync ]; then
                echo "Choose either --status or --unlink" >&2; exit 2
            fi
            case "$1" in -s|--status) MODE=status ;; *) MODE=unlink ;; esac
            ;;
        --dry-run) DRY_RUN=true ;;
        -t|--target)
            if [ "$#" -lt 2 ] || [ -z "$2" ]; then
                echo "--target requires a directory" >&2; exit 2
            fi
            TARGET_DIR="$2"
            case "$TARGET_DIR" in /*) ;; *) TARGET_DIR="$PWD/$TARGET_DIR" ;; esac
            CUSTOM_TARGET=true
            shift
            ;;
        -h|--help) print_usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; print_usage; exit 2 ;;
    esac
    shift
done

if $DRY_RUN; then echo "==> Dry run: no changes will be made"; fi
case "$MODE" in
    status) show_status ;;
    unlink) unlink_skills ;;
    sync) sync_skills ;;
esac
