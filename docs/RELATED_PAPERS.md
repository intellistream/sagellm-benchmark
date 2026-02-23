# Related Papers Summary — sagellm-benchmark

更新时间：2026-01-28

> 本文档收录 **评测方法与基准** 相关论文的走读心得与技术要点。

## Beyond FLOPs: Dissecting the Latency-Accuracy-Cost Trilemma in Heterogeneous LLM Serving
- 要解决：只盯峰值吞吐会忽略冷启动非线性、负扩展、长上下文导致的可靠性塌陷，导致评测对部署决策误导。
- 核心：声明式评测方法，把 Latency–Accuracy–Cost 三角同时摊开；在 Poisson 到达、不同硬件/量化/模型规模下系统性刻画。
- 关键发现（摘要表述）：
  - 小中模型下并行度提升可能负扩展（同步开销/不平衡/气泡）。
  - bit-width 对冷启动影响呈非线性（大模型更显著）。
  - 长上下文放大 P99 与可靠性问题。
- 可落到 sagellm-benchmark：
  - 把“冷启动”“P99”“失败率/可靠性”纳入默认报告，而不只是 TPS。
  - 输出部署决策树/推荐配置作为 benchmark 产物。

## HPC-Bench: A Comprehensive Benchmark for High Performance Computing Codes
- 要解决：LLM 代码评测偏功能正确性，但 HPC 优化取决于低层结构、内存行为与执行上下文。
- 核心：92 个真实工作负载、17 种 motif，自动化端到端评测（ correctness verification + reproducible performance measurement ）。
- 指标设计：correctness-gated、sampling-aware 的性能指标，衡量“有限采样预算下的可靠加速”。
- 对 sagellm-benchmark 的启发：
  - 对 kernel/系统优化也要 correctness gate（快但不等价不算）。
  - 把“采样预算 vs 可靠收益”显式化，避免 cherry-pick。

## MSKernelBench + CUDAMaster（Making LLMs Optimize Multi-Scenario CUDA Kernels Like Experts）
- 要解决：GPU kernel 自动优化多局限在 ML 算子，跨场景泛化与评测缺位。
- 核心：多场景基准（代数/LLM kernel/稀疏/HPC；FP32/BF16）+ 多智能体硬件感知优化系统，串起 profiling→编译→执行工具链。
- 对 sagellm-benchmark 的启发：
  - 给 sagellm 的关键 kernel 建立“多输入形状、多精度、多硬件”的基准矩阵。
  - 让 benchmark 同时产出：roofline 位置、带宽/算力瓶颈分类、可复现脚本。
