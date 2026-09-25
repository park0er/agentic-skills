#!/usr/bin/env bash
# rollie-data 一键发布脚本
# 用法：bash publish.sh <label> [--dry-run]

set -euo pipefail

LABEL="${1:?用法: publish.sh <label> [--dry-run]}"
DRY_RUN=false
[[ "${2:-}" == "--dry-run" ]] && DRY_RUN=true

GIT_DIR="/tmp/rollie-data/skill/rollie-data"
REPO_DIR="/tmp/rollie-data"
CONFIG_FILE="$REPO_DIR/.dev-config"
FACTORY_DIR="$HOME/Documents/Coding/PLAYGROUND/Skill_Factory/skills/rollie-data"
RELEASE_SCRIPT="$HOME/Documents/Coding/PLAYGROUND/Skill_Factory/release.sh"

# ============================================================
# Step 0: 读取或创建配置
# ============================================================
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "=== 首次使用，需要配置开发分支 ==="
    echo ""
    echo "当前分支："
    cd "$REPO_DIR" && git branch --list | sed 's/^/  /'
    echo ""
    read -rp "开发分支名（默认 xisheng）: " DEV_BRANCH
    DEV_BRANCH="${DEV_BRANCH:-xisheng}"
    read -rp "基础分支名（默认 develop）: " BASE_BRANCH
    BASE_BRANCH="${BASE_BRANCH:-develop}"

    cat > "$CONFIG_FILE" << EOF
DEV_BRANCH=$DEV_BRANCH
BASE_BRANCH=$BASE_BRANCH
EOF
    echo "✓ 配置已保存到 $CONFIG_FILE"
    echo ""
else
    source "$CONFIG_FILE"
fi

# ============================================================
# 检查 label
# ============================================================
if [[ "$LABEL" =~ ^(backup|v[0-9]+|[0-9]{8}|[0-9]{12})$ ]]; then
    echo "❌ label 不能是 '$LABEL'，请用具体描述（如 add-dsp-level2-enum）"
    exit 1
fi

echo "=== rollie-data 发布 ==="
echo "  label:        $LABEL"
echo "  开发分支:     $DEV_BRANCH"
echo "  基础分支:     $BASE_BRANCH"
echo "  git 目录:     $GIT_DIR"
echo "  Factory 目录: $FACTORY_DIR"
echo "  dry-run:      $DRY_RUN"
echo ""

# ============================================================
# Step 1: 精准复制到 Factory（排除敏感文件）
# ============================================================
echo "[1/6] 精准复制到 Factory..."

# 确保目标目录存在
mkdir -p "$FACTORY_DIR"

# 先清空 Factory 目录（保留 CHANGELOG.md 备份）
CHANGELOG_BACKUP=$(mktemp)
cp "$FACTORY_DIR/CHANGELOG.md" "$CHANGELOG_BACKUP" 2>/dev/null || true

# 用 rsync 精准复制，排除敏感文件
rsync -a --delete \
    --exclude='state/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='.git' \
    --exclude='.dev-config' \
    "$GIT_DIR/" "$FACTORY_DIR/"

# 恢复 state/.gitkeep（保留目录结构）
mkdir -p "$FACTORY_DIR/state"
touch "$FACTORY_DIR/state/.gitkeep"

# 恢复 CHANGELOG.md（如果 Factory 有更新的版本）
if [[ -f "$CHANGELOG_BACKUP" ]]; then
    # 比较两边的 CHANGELOG，保留更完整的那个
    FACTORY_LINES=$(wc -l < "$FACTORY_DIR/CHANGELOG.md" 2>/dev/null || echo 0)
    BACKUP_LINES=$(wc -l < "$CHANGELOG_BACKUP" 2>/dev/null || echo 0)
    if [[ $BACKUP_LINES -gt $FACTORY_LINES ]]; then
        cp "$CHANGELOG_BACKUP" "$FACTORY_DIR/CHANGELOG.md"
    fi
fi
rm -f "$CHANGELOG_BACKUP"

echo "  ✓ 已复制（排除 state/cookies、__pycache__、.DS_Store、.git）"

# ============================================================
# Step 2: 更新 CHANGELOG
# ============================================================
echo "[2/6] 更新 CHANGELOG..."
CHANGELOG="$FACTORY_DIR/CHANGELOG.md"
TODAY=$(date +%Y-%m-%d)
ENTRY="## $TODAY — $LABEL"

if grep -q "$ENTRY" "$CHANGELOG" 2>/dev/null; then
    echo "  ⚠ CHANGELOG 已包含 '$ENTRY'，跳过"
else
    TMP=$(mktemp)
    # 提取标题
    head -1 "$CHANGELOG" > "$TMP"
    echo "" >> "$TMP"
    echo "$ENTRY" >> "$TMP"
    echo "" >> "$TMP"
    echo "- TODO: 补充本次改动摘要" >> "$TMP"
    echo "" >> "$TMP"
    # 追加旧内容（跳过标题行）
    tail -n +2 "$CHANGELOG" >> "$TMP"
    mv "$TMP" "$CHANGELOG"
    echo "  ✓ 已添加条目：$ENTRY"
    echo "  ⚠ 请手动编辑 CHANGELOG.md 补充改动摘要"
fi

# ============================================================
# Step 3: dry-run
# ============================================================
echo "[3/6] dry-run 发布..."
cd ~/Documents/Coding/PLAYGROUND/Skill_Factory
if ./release.sh rollie-data "$LABEL" --dry-run 2>&1 | tail -8; then
    echo "  ✓ dry-run 通过"
else
    echo "  ❌ dry-run 失败，请检查"
    exit 1
fi

# ============================================================
# Step 4: 正式发布
# ============================================================
if [ "$DRY_RUN" = true ]; then
    echo "[4/6] 跳过正式发布（dry-run 模式）"
else
    echo "[4/6] 正式发布..."
    cd ~/Documents/Coding/PLAYGROUND/Skill_Factory
    if ./release.sh rollie-data "$LABEL" 2>&1 | tail -10; then
        echo "  ✓ 发布成功"
    else
        echo "  ❌ 发布失败"
        exit 1
    fi
fi

# ============================================================
# Step 5: 同步回 git 开发分支
# ============================================================
echo "[5/6] 同步回 git..."

# 切换到开发分支
cd "$REPO_DIR"
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$DEV_BRANCH" ]]; then
    echo "  ⚠ 当前在 $CURRENT_BRANCH 分支，切换到 $DEV_BRANCH..."
    git checkout "$DEV_BRANCH"
fi

# 精准同步回 git（从 Factory 复制回来）
rsync -a \
    --exclude='state/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    "$FACTORY_DIR/" "$GIT_DIR/"

# 恢复 state/.gitkeep
touch "$GIT_DIR/state/.gitkeep"

# 提交
cd "$REPO_DIR"
git add -A
if git diff --cached --quiet; then
    echo "  ⚠ 没有改动需要提交"
else
    git commit -m "feat: $LABEL" 2>&1 | head -3
    echo "  ✓ git commit 完成（$DEV_BRANCH 分支）"
fi

# ============================================================
# Step 6: 提醒审阅
# ============================================================
echo "[6/6] 完成"
echo ""
echo "=== 发布完成 ==="
echo "  archive: $(ls -t ~/Documents/Coding/PLAYGROUND/Skill_Factory/archives/rollie-data/ | head -1)"
echo ""
echo "  📋 下一步："
echo "  1. cd /tmp/rollie-data"
echo "  2. git push origin $DEV_BRANCH"
echo "  3. 给盛总审阅"
echo "  4. 盛总确认后：git checkout $BASE_BRANCH && git merge $DEV_BRANCH"
echo ""
echo "  ⚠ 不要自动 push $BASE_BRANCH！"
