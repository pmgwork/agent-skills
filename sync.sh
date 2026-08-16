#!/usr/bin/env bash
#
# sync.sh - Synchronize agent-skills into ~/.agents/skills (and configure aliases)
#

set -euo pipefail

# Determine repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SKILLS_SRC_DIR="${SCRIPT_DIR}/skills"
DEFAULT_TARGET_DIR="${HOME}/.agents/skills"
TARGET_DIR="${DEFAULT_TARGET_DIR}"

# Color codes
COLOR_RESET="\033[0m"
COLOR_BOLD="\033[1m"
COLOR_GREEN="\033[32m"
COLOR_YELLOW="\033[33m"
COLOR_BLUE="\033[34m"
COLOR_RED="\033[31m"
COLOR_GRAY="\033[90m"

# Modes
DRY_RUN=false
STATUS_ONLY=false
UNLINK_MODE=false
INSTALL_HOOK=false

print_usage() {
    cat <<EOF
${COLOR_BOLD}Usage:${COLOR_RESET} ./sync.sh [options]

${COLOR_BOLD}Options:${COLOR_RESET}
  -t, --target <path>   Specify target skills directory (default: ~/.agents/skills)
  -d, --dry-run         Show what would be done without making changes
  -s, --status          List current links and synchronization status
  -u, --unlink          Remove symlinks pointing to this repository
  --install-hook        Install Git hooks (post-commit, post-merge, post-checkout) for automatic sync
  -h, --help            Show this help message

${COLOR_BOLD}Examples:${COLOR_RESET}
  ./sync.sh                     # Sync skills to ~/.agents/skills
  ./sync.sh --dry-run           # Preview sync actions
  ./sync.sh --status            # Show current link status
  ./sync.sh -t ./.agents/skills # Sync to a project-local .agents/skills
  ./sync.sh --install-hook      # Enable auto-sync on git commit/merge/checkout
EOF
}

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--target)
            TARGET_DIR="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--status)
            STATUS_ONLY=true
            shift
            ;;
        -u|--unlink)
            UNLINK_MODE=true
            shift
            ;;
        --install-hook)
            INSTALL_HOOK=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${COLOR_RED}Unknown option: $1${COLOR_RESET}" >&2
            print_usage
            exit 1
            ;;
    esac
done

# Resolve absolute path for TARGET_DIR
if [[ "$TARGET_DIR" = /* ]]; then
    ABS_TARGET_DIR="$TARGET_DIR"
elif [[ "$TARGET_DIR" == ~* ]]; then
    ABS_TARGET_DIR="${TARGET_DIR/#\~/$HOME}"
else
    ABS_TARGET_DIR="$(pwd)/$TARGET_DIR"
fi

show_status() {
    echo -e "${COLOR_BOLD}${COLOR_BLUE}==> Skills Status${COLOR_RESET}"
    echo -e "Source: ${COLOR_GRAY}${SKILLS_SRC_DIR}${COLOR_RESET}"
    echo -e "Target: ${COLOR_GRAY}${ABS_TARGET_DIR}${COLOR_RESET}\n"

    if [[ ! -d "$ABS_TARGET_DIR" ]]; then
        echo -e "${COLOR_YELLOW}Target directory does not exist: ${ABS_TARGET_DIR}${COLOR_RESET}"
        return
    fi

    echo -e "${COLOR_BOLD}Skills in repository:${COLOR_RESET}"
    for skill_path in "$SKILLS_SRC_DIR"/*; do
        [[ -d "$skill_path" ]] || continue
        skill_name="$(basename "$skill_path")"
        target_link="${ABS_TARGET_DIR}/${skill_name}"

        if [[ -L "$target_link" ]]; then
            dest="$(readlink "$target_link" 2>/dev/null || true)"
            if [[ "$dest" == "$skill_path" ]]; then
                echo -e "  ${COLOR_GREEN}✔${COLOR_RESET} ${skill_name} -> ${COLOR_GRAY}${dest}${COLOR_RESET}"
            else
                echo -e "  ${COLOR_YELLOW}⚠${COLOR_RESET} ${skill_name} (points elsewhere: ${dest})"
            fi
        elif [[ -e "$target_link" ]]; then
            echo -e "  ${COLOR_YELLOW}⚠${COLOR_RESET} ${skill_name} (exists as regular file/directory in target)"
        else
            echo -e "  ${COLOR_RED}✖${COLOR_RESET} ${skill_name} (not linked)"
        fi
    done

    # Check for orphan links pointing to this repo
    echo -e "\n${COLOR_BOLD}Checking for orphan links in target:${COLOR_RESET}"
    local orphan_count=0
    for target_entry in "$ABS_TARGET_DIR"/*; do
        [[ -L "$target_entry" ]] || continue
        dest="$(readlink "$target_entry" 2>/dev/null || true)"
        if [[ "$dest" == "$SKILLS_SRC_DIR"/* ]]; then
            if [[ ! -e "$dest" ]]; then
                echo -e "  ${COLOR_RED}✖ Broken link:${COLOR_RESET} $(basename "$target_entry") -> ${dest}"
                orphan_count=$((orphan_count + 1))
            fi
        fi
    done
    if [[ $orphan_count -eq 0 ]]; then
        echo -e "  ${COLOR_GREEN}✔ No broken or orphan links.${COLOR_RESET}"
    fi

    # Check alias symlinks (~/.gemini/skills, ~/.claude/skills) if syncing to ~/.agents/skills
    if [[ "$ABS_TARGET_DIR" == "${HOME}/.agents/skills" ]]; then
        echo -e "\n${COLOR_BOLD}Agent directories alias check:${COLOR_RESET}"
        for alias_path in "${HOME}/.gemini/skills" "${HOME}/.claude/skills"; do
            if [[ -L "$alias_path" ]]; then
                alias_dest="$(readlink "$alias_path" 2>/dev/null || true)"
                if [[ "$alias_dest" == "$ABS_TARGET_DIR" || "$alias_dest" == "${HOME}/.agents/skills" ]]; then
                    echo -e "  ${COLOR_GREEN}✔${COLOR_RESET} ${alias_path} -> ${alias_dest}"
                else
                    echo -e "  ${COLOR_YELLOW}⚠${COLOR_RESET} ${alias_path} -> ${alias_dest}"
                fi
            elif [[ -d "$alias_path" ]]; then
                echo -e "  ${COLOR_YELLOW}ℹ${COLOR_RESET} ${alias_path} (exists as standalone directory)"
            else
                echo -e "  ${COLOR_GRAY}○${COLOR_RESET} ${alias_path} (not configured)"
            fi
        done
    fi
}

install_git_hooks() {
    local hooks_dir="${SCRIPT_DIR}/.git/hooks"
    if [[ ! -d "$hooks_dir" ]]; then
        echo -e "${COLOR_RED}Error: .git/hooks directory not found. Not a git repository?${COLOR_RESET}" >&2
        exit 1
    fi

    echo -e "${COLOR_BOLD}${COLOR_BLUE}==> Installing Git hooks for automatic sync${COLOR_RESET}"
    local hooks=("post-commit" "post-merge" "post-checkout")

    for hook_name in "${hooks[@]}"; do
        local hook_file="${hooks_dir}/${hook_name}"
        if [[ -f "$hook_file" ]] && ! grep -q "agent-skills sync" "$hook_file"; then
            echo -e "${COLOR_YELLOW}Appending sync hook to existing ${hook_name}${COLOR_RESET}"
            cat <<EOF >> "$hook_file"

# agent-skills sync
if [ -x "${SCRIPT_DIR}/sync.sh" ]; then
    "${SCRIPT_DIR}/sync.sh" >/dev/null 2>&1 || true
fi
EOF
        elif [[ ! -f "$hook_file" ]]; then
            cat <<EOF > "$hook_file"
#!/usr/bin/env bash
# agent-skills sync hook
if [ -x "${SCRIPT_DIR}/sync.sh" ]; then
    "${SCRIPT_DIR}/sync.sh"
fi
EOF
            chmod +x "$hook_file"
            echo -e "  ${COLOR_GREEN}✔${COLOR_RESET} Created ${hook_name}"
        else
            echo -e "  ${COLOR_GRAY}○${COLOR_RESET} ${hook_name} already configured"
        fi
    done
    echo -e "\n${COLOR_GREEN}Git hooks successfully installed! Auto-sync will run on commit, merge, and checkout.${COLOR_RESET}"
}

unlink_skills() {
    echo -e "${COLOR_BOLD}${COLOR_BLUE}==> Unlinking skills from ${ABS_TARGET_DIR}${COLOR_RESET}"
    local removed=0

    if [[ ! -d "$ABS_TARGET_DIR" ]]; then
        echo "Target directory does not exist."
        return
    fi

    for target_entry in "$ABS_TARGET_DIR"/*; do
        [[ -L "$target_entry" ]] || continue
        dest="$(readlink "$target_entry" 2>/dev/null || true)"
        if [[ "$dest" == "$SKILLS_SRC_DIR"/* ]]; then
            skill_name="$(basename "$target_entry")"
            if $DRY_RUN; then
                echo -e "  ${COLOR_YELLOW}[dry-run] Would remove:${COLOR_RESET} ${skill_name}"
            else
                rm "$target_entry"
                echo -e "  ${COLOR_RED}✔ Removed link:${COLOR_RESET} ${skill_name}"
            fi
            removed=$((removed + 1))
        fi
    done

    echo -e "${COLOR_GREEN}Unlinked ${removed} skill(s).${COLOR_RESET}"
}

sync_skills() {
    local dry_prefix=""
    if $DRY_RUN; then
        dry_prefix="${COLOR_YELLOW}[dry-run] ${COLOR_RESET}"
        echo -e "${COLOR_BOLD}${COLOR_YELLOW}Running in DRY-RUN mode. No files will be modified.${COLOR_RESET}\n"
    fi

    echo -e "${COLOR_BOLD}${COLOR_BLUE}==> Synchronizing skills${COLOR_RESET}"
    echo -e "Source: ${COLOR_GRAY}${SKILLS_SRC_DIR}${COLOR_RESET}"
    echo -e "Target: ${COLOR_GRAY}${ABS_TARGET_DIR}${COLOR_RESET}\n"

    if [[ ! -d "$ABS_TARGET_DIR" ]]; then
        if $DRY_RUN; then
            echo -e "${dry_prefix}Would create target directory: ${ABS_TARGET_DIR}"
        else
            mkdir -p "$ABS_TARGET_DIR"
            echo -e "${COLOR_GREEN}Created target directory:${COLOR_RESET} ${ABS_TARGET_DIR}"
        fi
    fi

    local linked_count=0
    local updated_count=0
    local skipped_count=0

    for skill_path in "$SKILLS_SRC_DIR"/*; do
        [[ -d "$skill_path" ]] || continue
        skill_name="$(basename "$skill_path")"
        target_link="${ABS_TARGET_DIR}/${skill_name}"

        if [[ -L "$target_link" ]]; then
            dest="$(readlink "$target_link" 2>/dev/null || true)"
            if [[ "$dest" == "$skill_path" ]]; then
                echo -e "  ${COLOR_GRAY}○ ${skill_name} (already linked)${COLOR_RESET}"
                skipped_count=$((skipped_count + 1))
                continue
            else
                if $DRY_RUN; then
                    echo -e "  ${dry_prefix}${COLOR_YELLOW}Would update link:${COLOR_RESET} ${skill_name} -> ${skill_path}"
                else
                    ln -sfn "$skill_path" "$target_link"
                    echo -e "  ${COLOR_GREEN}✔ Updated link:${COLOR_RESET} ${skill_name} -> ${skill_path}"
                fi
                updated_count=$((updated_count + 1))
            fi
        elif [[ -e "$target_link" ]]; then
            echo -e "  ${COLOR_YELLOW}⚠ Skipped ${skill_name}: regular file or directory already exists at target${COLOR_RESET}"
            skipped_count=$((skipped_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${dry_prefix}${COLOR_GREEN}Would create link:${COLOR_RESET} ${skill_name} -> ${skill_path}"
            else
                ln -sfn "$skill_path" "$target_link"
                echo -e "  ${COLOR_GREEN}✔ Created link:${COLOR_RESET} ${skill_name} -> ${skill_path}"
            fi
            linked_count=$((linked_count + 1))
        fi
    done

    # Clean up orphan links that point to deleted skills in this repo
    local orphan_count=0
    for target_entry in "$ABS_TARGET_DIR"/*; do
        [[ -L "$target_entry" ]] || continue
        dest="$(readlink "$target_entry" 2>/dev/null || true)"
        if [[ "$dest" == "$SKILLS_SRC_DIR"/* && ! -e "$dest" ]]; then
            orphan_name="$(basename "$target_entry")"
            if $DRY_RUN; then
                echo -e "  ${dry_prefix}${COLOR_RED}Would clean orphan link:${COLOR_RESET} ${orphan_name}"
            else
                rm "$target_entry"
                echo -e "  ${COLOR_RED}✔ Cleaned orphan link:${COLOR_RESET} ${orphan_name}"
            fi
            orphan_count=$((orphan_count + 1))
        fi
    done

    # Ensure ~/.gemini/skills and ~/.claude/skills aliases if target is ~/.agents/skills
    if [[ "$ABS_TARGET_DIR" == "${HOME}/.agents/skills" ]]; then
        for alias_target in "${HOME}/.gemini" "${HOME}/.claude"; do
            local alias_path="${alias_target}/skills"
            if [[ -d "$alias_target" && ! -e "$alias_path" ]]; then
                if $DRY_RUN; then
                    echo -e "\n  ${dry_prefix}${COLOR_GREEN}Would create alias:${COLOR_RESET} ${alias_path} -> ${ABS_TARGET_DIR}"
                else
                    ln -sfn "$ABS_TARGET_DIR" "$alias_path"
                    echo -e "\n  ${COLOR_GREEN}✔ Created alias:${COLOR_RESET} ${alias_path} -> ${ABS_TARGET_DIR}"
                fi
            fi
        done
    fi

    echo -e "\n${COLOR_BOLD}Summary:${COLOR_RESET} Linked: ${COLOR_GREEN}${linked_count}${COLOR_RESET}, Updated: ${COLOR_YELLOW}${updated_count}${COLOR_RESET}, Skipped: ${COLOR_GRAY}${skipped_count}${COLOR_RESET}, Orphan Cleaned: ${COLOR_RED}${orphan_count}${COLOR_RESET}"
}

# Main execution
if $STATUS_ONLY; then
    show_status
elif $INSTALL_HOOK; then
    install_git_hooks
elif $UNLINK_MODE; then
    unlink_skills
else
    sync_skills
fi
