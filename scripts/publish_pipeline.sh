#!/usr/bin/env bash
# =============================================================================
# sageLLM Benchmark 一键发布流水线
#
# 功能：运行基准测试 → 聚合结果 → 上传 HuggingFace → 触发 website 更新
#
# 用法：
#   ./scripts/publish_pipeline.sh [选项]
#
# 示例：
#   # 最常用：用 tiny-gpt2 跑全部 workloads，自动上传
#   ./scripts/publish_pipeline.sh --model sshleifer/tiny-gpt2 --backend-url http://localhost:8000/v1
#
#   # 指定 workload（Q1/Q2/.../Q8/all）
#   ./scripts/publish_pipeline.sh --model sshleifer/tiny-gpt2 --workload Q1
#
#   # 只聚合 + 上传，不跑测试（已有 outputs/）
#   ./scripts/publish_pipeline.sh --skip-run
#
#   # 只聚合，不上传（输出到 hf_data/ 后手动检查）
#   ./scripts/publish_pipeline.sh --skip-upload
#
#   # 完全跳过 HF，只生成本地文件
#   ./scripts/publish_pipeline.sh --local-only
# =============================================================================
set -euo pipefail

# --------------------------------------------------------------------------- #
# 颜色输出
# --------------------------------------------------------------------------- #
RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m'
CYAN='\033[0;36m' BOLD='\033[1m' NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC}  $*"; }
info() { echo -e "${CYAN}ℹ${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
fail() { echo -e "${RED}✗${NC}  $*" >&2; exit 1; }
step() { echo -e "\n${BOLD}[${STEP_NUM}/${TOTAL_STEPS}] $*${NC}"; STEP_NUM=$((STEP_NUM + 1)); }

# --------------------------------------------------------------------------- #
# 默认参数
# --------------------------------------------------------------------------- #
MODEL="sshleifer/tiny-gpt2"
BACKEND="cpu"
BACKEND_URL="http://localhost:8000/v1"
WORKLOAD="all"
HF_DATASET="${HF_DATASET:-intellistream/sagellm-benchmark-results}"

SKIP_RUN=false
SKIP_UPLOAD=false
LOCAL_ONLY=false
DRY_RUN=false
COMMIT_RESULTS=true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --------------------------------------------------------------------------- #
# 参数解析
# --------------------------------------------------------------------------- #
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)         MODEL="$2";       shift 2 ;;
    --backend)       BACKEND="$2";     shift 2 ;;
    --backend-url)   BACKEND_URL="$2"; shift 2 ;;
    --workload)      WORKLOAD="$2";    shift 2 ;;
    --hf-dataset)    HF_DATASET="$2";  shift 2 ;;
    --skip-run)      SKIP_RUN=true;    shift ;;
    --skip-upload)   SKIP_UPLOAD=true; shift ;;
    --local-only)    LOCAL_ONLY=true;  SKIP_UPLOAD=true; COMMIT_RESULTS=false; shift ;;
    --dry-run)       DRY_RUN=true;     shift ;;
    --no-commit)     COMMIT_RESULTS=false; shift ;;
    -h|--help)
      sed -n '/^# 用法/,/^# ===/p' "$0" | sed 's/^# //' | sed 's/^#//'
      exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
done

# --------------------------------------------------------------------------- #
# 步骤计数初始化
# --------------------------------------------------------------------------- #
STEP_NUM=1
if $SKIP_RUN; then
  TOTAL_STEPS=3
else
  TOTAL_STEPS=5
fi
$SKIP_UPLOAD || TOTAL_STEPS=$((TOTAL_STEPS + 1))

# --------------------------------------------------------------------------- #
# Banner
# --------------------------------------------------------------------------- #
echo -e "${BOLD}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║        sageLLM Benchmark 发布流水线                   ║"
echo "╠════════════════════════════════════════════════════════╣"
printf "║  模型    : %-45s ║\n" "${MODEL}"
printf "║  Workload: %-45s ║\n" "${WORKLOAD}"
printf "║  Backend : %-45s ║\n" "${BACKEND} (${BACKEND_URL})"
printf "║  HF 数据集: %-44s ║\n" "${HF_DATASET}"
printf "║  模式    : %-45s ║\n" "skip_run=${SKIP_RUN} skip_upload=${SKIP_UPLOAD} dry_run=${DRY_RUN}"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

cd "${REPO_ROOT}"

# --------------------------------------------------------------------------- #
# 环境检查
# --------------------------------------------------------------------------- #
step "环境检查"

if ! command -v sagellm-benchmark &>/dev/null; then
  fail "sagellm-benchmark 未安装。请运行: pip install isagellm-benchmark"
fi
ok "sagellm-benchmark 已安装: $(sagellm-benchmark --version 2>/dev/null || echo 'unknown')"

if ! command -v python3 &>/dev/null; then
  fail "python3 未找到"
fi
ok "Python: $(python3 --version)"

# 检查 HF token（上传需要）
if ! $SKIP_UPLOAD; then
  # 从 .env 文件加载（如果存在）
  if [[ -f "${HOME}/sagellm/.env" ]]; then
    # shellcheck disable=SC1090
    set -a; source "${HOME}/sagellm/.env"; set +a
    info "已加载 ~/.env: ${HOME}/sagellm/.env"
  fi
  if [[ -z "${HF_TOKEN:-}" ]]; then
    warn "HF_TOKEN 未设置，将跳过 HF 上传（使用 --skip-upload 明确跳过）"
    SKIP_UPLOAD=true
  else
    ok "HF_TOKEN 已配置 (${#HF_TOKEN} chars)"
  fi
fi

# --------------------------------------------------------------------------- #
# Step 1: 运行基准测试
# --------------------------------------------------------------------------- #
if ! $SKIP_RUN; then
  step "运行基准测试 (workload=${WORKLOAD}, model=${MODEL})"

  # 检查服务是否可达
  if ! curl -sf --max-time 5 "${BACKEND_URL}/models" > /dev/null 2>&1; then
    warn "Warning: ${BACKEND_URL}/models 无响应，继续（可能是流式端点）"
  else
    ok "Backend 服务可达: ${BACKEND_URL}"
  fi

  if $DRY_RUN; then
    info "[dry-run] sagellm-benchmark run --workload ${WORKLOAD} --backend ${BACKEND} ..."
  else
    sagellm-benchmark run \
      --workload "${WORKLOAD}" \
      --backend "${BACKEND}" \
      --backend-url "${BACKEND_URL}" \
      --model "${MODEL}" \
      --verbose
    ok "基准测试完成"
  fi

  # 统计输出文件
  output_count=$(find outputs/ -name "*_leaderboard.json" 2>/dev/null | wc -l || echo 0)
  ok "生成了 ${output_count} 个 leaderboard JSON 文件"
  if [[ "${output_count}" -eq 0 ]] && ! $DRY_RUN; then
    fail "未找到输出文件，请检查 benchmark 运行是否正常"
  fi
fi

# --------------------------------------------------------------------------- #
# Step 2: 聚合结果到 hf_data/
# --------------------------------------------------------------------------- #
step "聚合结果至 hf_data/"

if $DRY_RUN; then
  info "[dry-run] python scripts/aggregate_for_hf.py"
else
  python3 scripts/aggregate_for_hf.py
  ok "聚合完成"
fi

# 验证文件
for f in hf_data/leaderboard_single.json hf_data/leaderboard_multi.json; do
  if $DRY_RUN; then
    info "[dry-run] 跳过文件验证: ${f}"
  elif [[ -f "${f}" ]]; then
    count=$(python3 -c "import json; d=json.load(open('${f}')); print(len(d))" 2>/dev/null || echo "?")
    ok "${f} (${count} 条记录)"
  else
    warn "${f} 不存在，跳过"
  fi
done

# --------------------------------------------------------------------------- #
# Step 3: 验证 JSON schema
# --------------------------------------------------------------------------- #
step "验证 JSON 格式"

if $DRY_RUN; then
  info "[dry-run] python data/validate_schema.py"
elif [[ -f "data/validate_schema.py" ]]; then
  python3 data/validate_schema.py hf_data/leaderboard_single.json 2>/dev/null && ok "Schema 验证通过" || warn "Schema 验证有警告，继续发布"
else
  info "validate_schema.py 不在 data/，跳过验证"
fi

# --------------------------------------------------------------------------- #
# Step 4: 提交 hf_data/ 到 git（触发 upload-to-hf.yml Actions）
# --------------------------------------------------------------------------- #
if $COMMIT_RESULTS; then
  step "提交 hf_data/ 至 git"

  if $DRY_RUN; then
    info "[dry-run] git add hf_data/ && git commit && git push"
  else
    git add hf_data/
    if git diff --cached --quiet; then
      info "hf_data/ 无变更，跳过 commit"
    else
      COMMIT_MSG="feat: add benchmark results $(date +%Y%m%d) - model=${MODEL} workload=${WORKLOAD} [auto-publish]"
      git commit -m "${COMMIT_MSG}"
      git push
      ok "已推送到 git，GitHub Actions 将自动上传到 HuggingFace"
    fi
  fi
fi

# --------------------------------------------------------------------------- #
# Step 5: 直接上传到 HF（可选，跳过时依赖 Actions）
# --------------------------------------------------------------------------- #
if ! $SKIP_UPLOAD; then
  step "直接上传到 HuggingFace"

  if $DRY_RUN; then
    info "[dry-run] python scripts/upload_to_hf.py"
  else
    HF_TOKEN="${HF_TOKEN}" python3 scripts/upload_to_hf.py
    ok "上传完成"
  fi
fi

# --------------------------------------------------------------------------- #
# 完成摘要
# --------------------------------------------------------------------------- #
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗"
echo "║              ✅  发布流水线完成！                      ║"
echo "╠════════════════════════════════════════════════════════╣"
echo -e "║  HF 数据集  : https://huggingface.co/datasets/${HF_DATASET:0:20}...${NC}"
echo -e "${BOLD}${GREEN}║  Website    : https://intellistream.github.io/sagellm-website"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if $COMMIT_RESULTS && ! $DRY_RUN; then
  info "GitHub Actions upload-to-hf.yml 正在运行，约 2-3 分钟后 website 数据更新"
  info "Actions 进度: https://github.com/intellistream/sagellm-benchmark/actions"
fi
