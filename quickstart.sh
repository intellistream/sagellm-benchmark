#!/bin/bash
# sagellm-benchmark: Quick Start
# Benchmark suite

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}sagellm-benchmark Quick Start${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo -e "${BLUE}📂 Project root: ${NC}$PROJECT_ROOT"
echo ""

echo -e "${YELLOW}${BOLD}Step 1/3: Installing Git Hooks${NC}"

HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
TEMPLATE_DIR="$PROJECT_ROOT/hooks"

if [ -d "$HOOKS_DIR" ]; then

    if [ -f "$TEMPLATE_DIR/pre-commit" ]; then
        cp "$TEMPLATE_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
        chmod +x "$HOOKS_DIR/pre-commit"
        echo -e "${GREEN}✓ Installed pre-commit hook${NC}"
    else
        echo -e "${YELLOW}⚠  pre-commit template not found, skipping${NC}"
    fi

    if [ -f "$TEMPLATE_DIR/pre-push" ]; then
        cp "$TEMPLATE_DIR/pre-push" "$HOOKS_DIR/pre-push"
        chmod +x "$HOOKS_DIR/pre-push"
        echo -e "${GREEN}✓ Installed pre-push hook${NC}"
    else
        echo -e "${YELLOW}⚠  pre-push template not found, skipping${NC}"
    fi
else
    echo -e "${YELLOW}⚠  .git 目录不存在，跳过 hooks 安装${NC}"
fi

echo ""

echo -e "${YELLOW}${BOLD}Step 2/3: Checking Python${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" || {
    echo -e "${RED}✗ Python $PYTHON_VERSION 版本过低，需要 >= 3.10${NC}"
    exit 1
}
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

echo ""

echo -e "${YELLOW}${BOLD}Step 3/3: Install package (editable)${NC}"
echo -e "${BLUE}📦 Installing isagellm-benchmark...${NC}"
pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet

echo ""

echo ""
echo -e "${GREEN}${BOLD}✓ Setup Complete${NC}"
echo ""
echo -e "${BLUE}${BOLD}Next Steps:${NC}"
echo -e "  ${CYAN}1.${NC} 运行测试: ${CYAN}pytest -v${NC}"
echo -e "  ${CYAN}2.${NC} 运行基准: ${CYAN}./run_benchmark.sh${NC}"
echo -e "  ${CYAN}3.${NC} 代码规范: ${CYAN}ruff check .${NC}"
echo -e "  ${CYAN}4.${NC} 阅读文档: ${CYAN}cat README.md${NC}"
