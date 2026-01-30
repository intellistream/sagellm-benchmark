# sagellm-benchmark Copilot Instructions

## 仓库信息

| 字段 | 值 |
|-----|-----|
| 仓库名 | sagellm-benchmark |
| PyPI 包名 | `isagellm-benchmark` |
| 导入命名空间 | `sagellm_benchmark` |
| 主要职责 | 性能基准测试套件（独立的 benchmark suite） |

## 🚨 核心开发原则

### Protocol-First（协议优先）
- ❌ **禁止** 在协议冻结前实现功能
- ✅ **必须** 先定义 request/response schema、错误码、指标字段

### CPU-First（默认 CPU）
- ✅ **必须** 默认使用 CPU
- ✅ **必须** CI 测试可在无 GPU 环境运行

### Fail-Fast（快速失败）
- ❌ **禁止** 静默回退、隐式默认值
- ✅ **必须** 配置缺失时抛出明确错误

### Protocol Compliance（强制）
- ✅ **必须** 所有实现遵循 Protocol v0.1（sagellm-docs/docs/specs/protocol_v0.1.md）
- ✅ **必须** 任何全局共享定义（字段/错误码/指标/ID/Schema）先补充到 Protocol

## 编码规范

- Python 3.10+
- 强制类型注解：`from __future__ import annotations`
- Docstring：Google 风格
- 行长度：100 字符
- Linter：ruff

## 📝 CHANGELOG 更新规则（强制）

**🚨 每次推送前必须更新 CHANGELOG.md！**

### 更新 CHANGELOG 的时机

- ✅ **必须** 在每次 `git push` 前更新 CHANGELOG.md
- ✅ **必须** 在 `[Unreleased]` 部分添加本次改动
- ✅ **必须** 使用正确的分类（Added/Changed/Fixed/Removed）
- ✅ **必须** 在版本发布时，将 `[Unreleased]` 改为版本号和日期

### CHANGELOG 格式

遵循 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) 规范：

```markdown
## [Unreleased]

### Added
- 新增的功能描述

### Changed
- 改动的功能描述

### Fixed
- 修复的问题描述

### Removed
- 移除的功能描述
```

### 示例工作流

```bash
# 1. 修改代码
vim src/sagellm_benchmark/some_file.py

# 2. 更新 CHANGELOG.md（强制！）
vim CHANGELOG.md
# 在 [Unreleased] 部分添加：
# ### Added
# - 新增 XXX 功能

# 3. 提交
git add .
git commit -m "feat: add XXX feature"

# 4. 推送（pre-push hook 会检查 CHANGELOG）
git push
```

## 📦 PyPI 发布流程

**必须使用 `sage-pypi-publisher` 工具发布，且使用 private 模式（字节码编译）。**

## 🚨 发布规范（0.4.0 版本更新）

**每个仓库必须单独发布（交互式 PyPI 发布）**

- ✅ **必须** 每个仓库独立发布（交互式 PyPI 发布）
- ❌ **禁止** 一次性批量发布多个仓库
- ✅ **必须** 使用 sage-pypi-publisher（private 模式）
- ✅ **必须** 发布前更新 CHANGELOG 并通过 pytest/ruff
- ✅ **必须** 每次改动后更新版本并重新发布

**为什么要逐仓库发布？**

1. **风险隔离**：单个仓库发布失败不影响其他仓库
2. **版本精确控制**：每个包有独立的版本号和发布节奏
3. **CHANGELOG 可追溯**：每个包的改动独立记录，便于审计
4. **测试充分**：逐个仓库测试通过后再发布，降低线上风险

### 安装发布工具
```bash
pip install isage-pypi-publisher
```

### 发布命令
```bash
# 构建并发布到 PyPI（private 模式 - 默认）
cd /path/to/sagellm-benchmark
sage-pypi-publisher build . --upload --no-dry-run

# 或显式指定 private 模式
sage-pypi-publisher build . --upload --no-dry-run --mode private
```

### ⚠️ 重要提醒
- ❌ **禁止** 使用 `--mode public`（会暴露源码）
- ❌ **禁止** 直接使用 `pip` 或 `twine` 发布
- ✅ **必须** 使用 `sage-pypi-publisher` 的 private 模式
- ✅ **必须** 在发布前确保所有测试通过

### 版本管理（4 位强制）
- ✅ **必须** 使用 4 位版本号：`MAJOR.MINOR.PATCH.BUILD`
- 修改 `pyproject.toml` 中的 `version` 字段（例如：`0.4.0.0`）
- 功能改动：`0.4.0.0 → 0.5.0.0`（MINOR +1）
- Bug 修复：`0.4.0.0 → 0.4.0.1`（BUILD +1）
- 依赖版本范围：umbrella `>=0.4.0.0,<0.5.0`
- 遵循 SemVer 语义化版本规范
- 发布前确认版本号已更新

## 测试

```bash
# 运行测试
pytest -v

# 覆盖率
pytest --cov=sagellm_benchmark --cov-report=html

# Lint
ruff check .
ruff format .
```

## 依赖层级

```
isagellm (umbrella 包)
    ↓
isagellm-benchmark (本仓库 - 独立的 benchmark suite，依赖 umbrella)
```

**关键说明**：
- benchmark 是独立的性能测试套件
- 依赖 `isagellm` umbrella 包来进行完整的性能测试
- 不属于核心引擎层级，是测试工具


## GitHub Issue Labels 规范

### 必须使用的 Labels

创建 issue 时，**必须**使用以下标准 labels：

#### 1. 仓库关联 Labels（选择相关的仓库）
- `sagellm-protocol` - 与 protocol 包相关
- `sagellm-backend` - 与 backend 包相关
- `sagellm-core` - 与 core 包相关
- `sagellm-kv-cache` - 与 kv-cache 包相关（KV Transfer）
- `sagellm-control-plane` - 与 control-plane 包相关
- `sagellm-gateway` - 与 gateway 包相关
- `sagellm-compression` - 与 compression 包相关

#### 2. 功能类型 Labels（选择主要类型）
- `performance` - 性能优化和 benchmark
- `reliability` - 可靠性和容错
- `tools` - 开发和调试工具
- `integration` - 与其他模块集成
- `testing` - 测试基础设施
- `documentation` - 文档改进
- `enhancement` - 新功能增强
- `bug` - Bug 修复

#### 3. 优先级（可选，使用 title 前缀或 milestone）
- 在 title 中使用 `[P0]`, `[P1]`, `[P2]` 前缀
- 或使用 GitHub Milestones 管理优先级

### Issue 命名规范

```
[类型] 简短描述

示例：
- [Performance] CollectiveOps 性能 Benchmark 和优化
- [Integration] 与 sagellm-kv-cache KV Transfer 深度集成
- [Reliability] 通信容错和重试机制
- [Tools] 通信诊断和调试工具
```

### Labels 使用示例

```bash
# 创建性能优化 issue，关联 sagellm-backend
gh issue create \
  --title "[Performance] AllReduce 算法自适应选择" \
  --label "performance,sagellm-backend,enhancement"

# 创建集成 issue，关联多个仓库
gh issue create \
  --title "[Integration] 与 sagellm-kv-cache KV Transfer 深度集成" \
  --label "integration,sagellm-kv-cache,sagellm-comm"
```


## 相关文档

- 主文档仓库：https://github.com/intellistream/sagellm-docs
- Protocol 规范：`docs/specs/protocol_v0.1.md`（见 sagellm-docs）
