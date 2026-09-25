# shellcheck shell=bash
# Source this file for consistent logging helpers across all scripts.

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  _CLR_RESET='\033[0m'
  _CLR_DIM='\033[2m'
  _CLR_RED='\033[31m'
  _CLR_GREEN='\033[32m'
  _CLR_YELLOW='\033[33m'
  _CLR_BLUE='\033[34m'
  _CLR_BOLD='\033[1m'
else
  _CLR_RESET=''; _CLR_DIM=''; _CLR_RED=''; _CLR_GREEN=''; _CLR_YELLOW=''; _CLR_BLUE=''; _CLR_BOLD=''
fi

_ts() { date '+%H:%M:%S'; }

log_info()  { printf "${_CLR_DIM}[%s]${_CLR_RESET} ${_CLR_BLUE}INFO${_CLR_RESET}  %s\n" "$(_ts)" "$*"; }
log_ok()    { printf "${_CLR_DIM}[%s]${_CLR_RESET} ${_CLR_GREEN}OK${_CLR_RESET}    %s\n" "$(_ts)" "$*"; }
log_warn()  { printf "${_CLR_DIM}[%s]${_CLR_RESET} ${_CLR_YELLOW}WARN${_CLR_RESET}  %s\n" "$(_ts)" "$*" >&2; }
log_error() { printf "${_CLR_DIM}[%s]${_CLR_RESET} ${_CLR_RED}ERROR${_CLR_RESET} %s\n" "$(_ts)" "$*" >&2; }

hr() { printf "${_CLR_DIM}%s${_CLR_RESET}\n" "────────────────────────────────────────────────────"; }
bold() { printf "${_CLR_BOLD}%s${_CLR_RESET}" "$*"; }
