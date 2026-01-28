# Benchmark Results Sync

## 自动同步机制

sagellm-website 会**自动定期**从本仓库拉取最新的 leaderboard 数据，无需任何配置。

## 同步方式

### 1. 自动同步（推荐）⏰

- **频率**：每天 UTC 00:00 自动运行
- **范围**：拉取 `outputs/` 下所有 `*_leaderboard.json` 文件
- **结果**：自动创建 PR 到 sagellm-website

### 2. 手动触发 🖱️

如果希望立即同步，可以手动触发：

1. 访问 sagellm-website Actions 页面：  
   https://github.com/intellistream/sagellm-website/actions/workflows/sync-benchmark-results.yml

2. 点击 "Run workflow" 按钮

3. 选择 branch (通常是 main)

4. 点击绿色的 "Run workflow" 按钮

5. 等待几分钟，查看自动创建的 PR

## 查看同步结果

同步完成后，会在 sagellm-website 自动创建 PR：

- 标题：`[Auto] Sync Benchmark Results`
- 标签：`automated`, `benchmark-sync`, `data-update`
- 内容：包含同步的文件数量和来源信息

审核并 merge PR 后，leaderboard 数据就会出现在 website 上。

## 文件映射

**本仓库（源）：**
```
outputs/
└── cpu/
    └── gpt2/
        └── short_20260128_005/
            └── short_input_leaderboard.json
```

**website（目标）：**
```
data/results/
└── cpu/
    └── gpt2/
        └── short_20260128_005_short_input_leaderboard.json
```

## 注意事项

1. ✅ 只同步 `*_leaderboard.json` 文件（其他文件被忽略）
2. ✅ 保留所有历史运行结果（使用 run_id 前缀避免冲突）
3. ✅ 增量同步（只复制新的或更新的文件）
4. ⚠️ 定时同步每天一次，如需立即同步请手动触发

## 故障排查

### Q: 为什么没有看到 PR？

- 检查是否有新的 leaderboard 文件（相比上次同步）
- 查看 sagellm-website 的 Actions 运行日志
- 如果所有数据已同步，不会创建新的 PR

### Q: 如何验证文件已同步？

访问 sagellm-website 仓库：
```bash
# 查看 data/results/ 目录
https://github.com/intellistream/sagellm-website/tree/main/data/results
```

### Q: 同步失败怎么办？

1. 查看 workflow 运行日志
2. 检查 benchmark 仓库的 outputs/ 目录是否有 leaderboard 文件
3. 在 sagellm-website 提 issue
