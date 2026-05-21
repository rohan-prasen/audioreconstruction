#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

cleanup() {
    echo ""
    echo -e "\033[2m   ───────────────────────────────────────────────────\033[0m"
    echo -e "   \033[33m●\033[0m  \033[2mShutting down...\033[0m"
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null && \
        echo -e "   \033[32m✓\033[0m  \033[2mBackend stopped\033[0m"
    [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null && \
        echo -e "   \033[32m✓\033[0m  \033[2mFrontend stopped\033[0m"
    wait 2>/dev/null
    echo ""
    echo -e "   \033[32m\033[1mGoodbye!\033[0m"
    echo ""
}
trap cleanup EXIT INT TERM

BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[36m"
MAGENTA="\033[35m"
BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
WHITE="\033[37m"
RESET="\033[0m"

echo ""
echo -e "${RESET}"
echo -e "${GREEN}${BOLD}"
cat << 'EOF'
   ╔ ════════════════════════════════════════════════ ╗
   ║                                                  ║
   ║     █████╗ ██╗   ██╗██████╗ ██╗ ██████╗          ║
   ║    ██╔══██╗██║   ██║██╔══██╗██║██╔═══██╗         ║
   ║    ███████║██║   ██║██║  ██║██║██║   ██║         ║
   ║    ██╔══██║██║   ██║██║  ██║██║██║   ██║         ║
   ║    ██║  ██║╚██████╔╝██████╔╝██║╚██████╔╝         ║
   ║    ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝          ║
   ║                                                  ║
   ║    ██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗   ║
   ║    ██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║   ║
   ║    ██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║   ║
   ║    ██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║   ║
   ║    ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║   ║
   ║    ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ║
   ║                                                  ║
   ╚ ════════════════════════════════════════════════ ╝
EOF
echo -e "${RESET}"
echo -e "   ${DIM}GAN-based audio super-resolution  ·  MP3 → FLAC${RESET}"
echo ""
echo -e "   ${DIM}───────────────────────────────────────────────────${RESET}"
echo ""
echo -e "   ${GREEN}▸${RESET} ${BOLD}Backend${RESET}   ${CYAN}http://localhost:${BACKEND_PORT}${RESET}"
echo -e "   ${GREEN}▸${RESET} ${BOLD}Frontend${RESET}  ${CYAN}http://localhost:${FRONTEND_PORT}${RESET}"
echo ""
echo -e "   ${DIM}Press ${WHITE}${BOLD}Ctrl+C${RESET}${DIM} to stop both servers.${RESET}"
echo -e "   ${DIM}───────────────────────────────────────────────────${RESET}"
echo ""

log() {
    local color="$1" icon="$2" msg="$3"
    echo -e "   ${color}${icon}${RESET}  ${msg}"
}

# --- Backend ---
log "$YELLOW" "●" "${BOLD}Starting backend${RESET} ${DIM}(FastAPI on :${BACKEND_PORT})${RESET}"
cd "$ROOT"
VITE_BACKEND_URL="http://localhost:${BACKEND_PORT}" \
  uv run uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload &
BACKEND_PID=$!
log "$GREEN" "✓" "${DIM}Backend started${RESET}  ${DIM}pid=${BACKEND_PID}${RESET}"

# --- Frontend ---
log "$YELLOW" "●" "${BOLD}Installing frontend dependencies...${RESET}"
cd "$ROOT/frontend"

VITE_BACKEND_URL="http://localhost:${BACKEND_PORT}" \
  bun install --silent 2>/dev/null || bun install
log "$GREEN" "✓" "${DIM}Dependencies installed${RESET}"

log "$YELLOW" "●" "${BOLD}Starting frontend${RESET} ${DIM}(Vite on :${FRONTEND_PORT})${RESET}"
VITE_BACKEND_URL="http://localhost:${BACKEND_PORT}" \
  bun run dev -- --port "$FRONTEND_PORT" &
FRONTEND_PID=$!
log "$GREEN" "✓" "${DIM}Frontend started${RESET}  ${DIM}pid=${FRONTEND_PID}${RESET}"

echo ""
echo -e "   ${DIM}───────────────────────────────────────────────────${RESET}"
echo -e "   ${GREEN}${BOLD}Ready!${RESET}  ${DIM}Open${RESET} ${CYAN}http://localhost:${FRONTEND_PORT}${RESET} ${DIM}in your browser.${RESET}"
echo -e "   ${DIM}───────────────────────────────────────────────────${RESET}"
echo ""

wait
