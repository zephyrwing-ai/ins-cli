#!/bin/bash
# Google Chrome Profile Backup & Restore Tool
# Usage:
#   ./backup_chrome.sh backup   — 备份当前 Chrome 配置
#   ./backup_chrome.sh restore  — 从备份恢复 Chrome 配置
#   ./backup_chrome.sh list     — 列出所有备份

set -euo pipefail

CHROME_DIR="$HOME/Library/Application Support/Google/Chrome"
BACKUP_BASE="$HOME/.chrome-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 需要备份的关键文件/目录
ITEMS=(
    "Default/Cookies"
    "Default/Cookies-journal"
    "Default/Extensions"
    "Default/Extension Rules"
    "Default/Local Extension Settings"
    "Default/Preferences"
    "Default/Secure Preferences"
    "Default/Login Data"
    "Default/Login Data-journal"
    "Default/Web Data"
    "Default/Bookmarks"
    "Default/Favicons"
    "Default/History"
    "Default/Sessions"
    "Default/Session Storage"
    "Default/Local Storage"
    "Local State"
)

backup() {
    echo "=== Backing up Google Chrome profile ==="
    BACKUP_DIR="${BACKUP_BASE}/${TIMESTAMP}"
    mkdir -p "${BACKUP_DIR}"

    for item in "${ITEMS[@]}"; do
        src="${CHROME_DIR}/${item}"
        if [ -e "$src" ]; then
            # 创建目标目录结构
            dst="${BACKUP_DIR}/${item}"
            mkdir -p "$(dirname "$dst")"

            if [ -d "$src" ]; then
                cp -R "$src" "$dst"
            else
                cp "$src" "$dst"
            fi
            echo "  ✓ ${item}"
        else
            echo "  ✗ ${item} (not found)"
        fi
    done

    # 记录备份大小
    SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo ""
    echo "Backup saved to: ${BACKUP_DIR}"
    echo "Size: ${SIZE}"

    # 只保留最近 5 个备份
    COUNT=$(ls -1d "${BACKUP_BASE}"/* 2>/dev/null | wc -l | tr -d ' ')
    if [ "$COUNT" -gt 5 ]; then
        OLDEST=$(ls -1d "${BACKUP_BASE}"/* | head -1)
        echo "Removing old backup: ${OLDEST}"
        rm -rf "$OLDEST"
    fi
}

restore() {
    echo "=== Restoring Google Chrome profile ==="

    if [ ! -d "${BACKUP_BASE}" ]; then
        echo "No backups found!"
        exit 1
    fi

    # 列出可用备份
    echo "Available backups:"
    ls -1d "${BACKUP_BASE}"/* | cat -n
    echo ""

    # 如果指定了备份编号
    if [ -n "${2:-}" ]; then
        BACKUP_DIR=$(ls -1d "${BACKUP_BASE}"/* | sed -n "${2}p")
    else
        # 默认用最新的
        BACKUP_DIR=$(ls -1d "${BACKUP_BASE}"/* | tail -1)
    fi

    if [ ! -d "$BACKUP_DIR" ]; then
        echo "Backup not found: ${BACKUP_DIR}"
        exit 1
    fi

    echo "Restoring from: ${BACKUP_DIR}"
    echo ""
    echo "Please close Google Chrome before restoring!"
    read -p "Continue? (y/N) " confirm
    if [ "$confirm" != "y" ]; then
        echo "Aborted."
        exit 0
    fi

    for item in "${ITEMS[@]}"; do
        src="${BACKUP_DIR}/${item}"
        if [ -e "$src" ]; then
            dst="${CHROME_DIR}/${item}"
            mkdir -p "$(dirname "$dst")"

            if [ -d "$src" ]; then
                rm -rf "$dst"
                cp -R "$src" "$dst"
            else
                cp "$src" "$dst"
            fi
            echo "  ✓ ${item}"
        fi
    done

    echo ""
    echo "Restore complete! Open Google Chrome to verify."
}

list() {
    if [ ! -d "${BACKUP_BASE}" ]; then
        echo "No backups found."
        exit 0
    fi

    echo "=== Google Chrome Backups ==="
    for dir in $(ls -1d "${BACKUP_BASE}"/* 2>/dev/null); do
        SIZE=$(du -sh "$dir" | cut -f1)
        NAME=$(basename "$dir")
        echo "  ${NAME}  (${SIZE})"
    done
}

case "${1:-}" in
    backup)  backup ;;
    restore) restore "$@" ;;
    list)    list ;;
    *)
        echo "Google Chrome Profile Backup & Restore"
        echo ""
        echo "Usage: $0 {backup|restore|list}"
        echo ""
        echo "  backup   — Backup current profile (extensions, cookies, bookmarks, etc.)"
        echo "  restore  — Restore from latest backup (or specify number)"
        echo "  list     — List all backups"
        ;;
esac
