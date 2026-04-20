#!/bin/bash

set -euo pipefail

# =================================================================
# CONFIGURATION
# =================================================================
CURRENT_TTY=$(tty)      # e.g. /dev/pts/1 or /dev/tty2
DRY_RUN=0               # 0=Run, 1=Show what would happen
TARGET_USER=""          # Leave empty to target all console users

# =================================================================
# FUNCTIONS
# =================================================================

print_info() {
    echo "[INFO] $(date '+%F %T') - $1"
}

print_warning() {
    echo "[WARN] $(date '+%F %T') - $1"
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Error: This script requires Root (sudo) privileges."
        exit 1
    fi
}

get_console_users() {
    # Check for systemd (loginctl) first
    if command -v loginctl &> /dev/null; then
        # Use systemd loginctl (most reliable for TTY sessions)
        # -u is the user ID. -s shows sessions.
        # Filter for actual console TTYs (tty1, tty2, tty3...)
        loginctl list-sessions 2>/dev/null | grep -E '\btty[0-9]+\bt' | while read -r line; do
            # loginctl output columns: ID, USER, SESSION, SEAT, PID, TTY, TTY_TYPE, USER_CLASS
            # Columns might vary slightly, but USER and TTY are usually consistent.
            # Extract user and TTY type.
            session_user=$(echo "$line" | awk '{print $2}')
            session_tty=$(echo "$line" | awk '{print $6}')
            session_pid=$(echo "$line" | awk '{print $5}')
            
            # Filter if we are targeting a specific user or ALL
            if [ -z "$TARGET_USER" ] || [ "$session_user" = "$TARGET_USER" ]; then
                echo "$session_user|$session_tty|$session_pid"
            fi
        done
    else
        # Fallback for non-systemd (SysV/older) systems using 'w'
        print_info "Detected non-systemd or legacy environment. Using 'w' and 'pkill'."
        w | awk 'NR>1 {print $1, $2, $8}' | while read -r user tty pid; do
            if [[ "$tty" =~ ^/dev/tty[0-9]+$ ]] || [[ "$tty" =~ ^/dev/ttyS[0-9]+$ ]]; then
                # Exclude current running shell
                if [ "$(tty)" != "$tty" ]; then
                    echo "$user|$tty|$pid"
                fi
            fi
        done
    fi
}

execute_kill() {
    while IFS='|' read -r user tty pid; do
        if [ $DRY_RUN -eq 1 ]; then
            print_warning "Would terminate: User=$user, TTY=$tty, PID=$pid"
        else
            print_info "Terminating: User=$user, TTY=$tty, PID=$pid"
            # Try loginctl (softer) first, then pkill (force) if needed
            if command -v loginctl &> /dev/null; then
                loginctl terminate-user "$user" &>/dev/null 2>&1 || true
            fi
            # Fallback
            kill -TERM "$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
        fi
    done
}

print_help() {
    echo "Usage: $0 [OPTIONS] [TARGET_USER]"
    echo "Options:"
    echo "  -n, --dry-run  Show what would happen without killing"
    echo "  -u, --user     Target specific user (e.g. 'u1' or 'root')"
    echo "  -a, --all      Target ALL console sessions (default)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Log out all local console sessions (tty1-6)"
    echo "  $0 --dry-run          # Preview which sessions will be killed"
    echo "  $0 --user root        # Log out only the root user"
}

# =================================================================
# MAIN LOGIC
# =================================================================

parse_args() {
    while getopts "hnu:a" opt; do
        case $opt in
            h) print_help; exit 0 ;;
            n) DRY_RUN=1 ;;
            u) TARGET_USER="$OPTARG" ;;
            a) TARGET_USER="" ;; # All users (reset target)
            \?) echo "Invalid option: -$OPTARG" ;;
        esac
    done
    shift $((OPTIND-1))
}

# Check Root
check_root

# Parse Arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--dry-run) DRY_RUN=1; shift ;;
        -u|--user) TARGET_USER="$2"; shift 2 ;;
        -a|--all) TARGET_USER=""; shift 2 ;;
        -h|--help) print_help; exit 0 ;;
        *) 
            # If no flag, treat as direct user argument
            TARGET_USER="$1" 
            shift
            ;;
    esac
done

# Default to all if no user specified
if [ -z "$TARGET_USER" ]; then
    TARGET_USER="ALL"
fi

echo "========================================"
echo "Console TTY Session Logger"
echo "Current TTY: $CURRENT_TTY"
echo "Mode: $([ $DRY_RUN -eq 1 ] && echo "DRY-RUN" || echo "EXECUTE")"
echo "Target: $TARGET_USER"
echo "========================================"

# Get active console users
echo ""
echo "--- Scanning Active Sessions ---"

# Capture output to a variable array to prevent subshell issues
declare -a SESSIONS=()
while IFS='|' read -r user tty pid; do
    SESSIONS+=("$user|$tty|$pid")
done < <(get_console_users)

if [ ${#SESSIONS[@]} -eq 0 ]; then
    echo "No active console sessions found for target '$TARGET_USER'."
    exit 0
fi

echo "--- Found ${#SESSIONS[@]} Sessions ---"

# Execute Kill
for session in "${SESSIONS[@]}"; do
    IFS='|' read -r user tty pid <<< "$session"
    echo "$user|$tty|$pid"
    if [ $DRY_RUN -eq 0 ]; then
        kill -TERM "$pid" 2>/dev/null || true
        print_info "Process $pid sent SIGTERM for $user on $tty"
    fi
    sleep 0.5 # Brief pause
done

echo ""
echo "--- Final Check ---"
# Re-scan briefly to ensure they are gone
w | grep -E 'tty[0-9]+' | wc -l
if [ $DRY_RUN -eq 1 ]; then
    echo "[DRY-RUN] Done."
else
    echo "Done."
fi
