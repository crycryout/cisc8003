# CISC8003 / Homework 1 实验接续

**下一步：在 H800 主机上启动 Codex，先读取 [`AGENTS.md`](AGENTS.md) 和 [完整接续说明](docs/H800_CODEX_HANDOFF.md)。**

当前已完成算法、运行脚本、真实 Hadoop 本地验证和中图全量结果；**四台实验室机器的集群部署、性能测量和截图尚未完成**。本仓库用于把工作交接给可访问实验室内网的 Codex。

| 物理机器 | 规划角色 |
|---|---|
| 独立 Jetson Thor | master：NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer |
| H800 所在的 NUMA 双节点主机 | worker1：DataNode、NodeManager |
| 第一台独立 RTX 5090 主机 | worker2：DataNode、NodeManager |
| 第二台独立 RTX 5090 主机 | worker3：DataNode、NodeManager |

不再使用云服务器；H800 不拆成两台，GPU 不参与 Hadoop 作业。主机名、CPU 架构、SSH 地址和账号仍须在实验室确认；文档中的 `thor/h800/rtx5090a/rtx5090b` 都是示例名。

## 从 H800 接续

```bash
git clone https://github.com/crycryout/cisc8003.git
cd cisc8003
codex
```

给 Codex 的完整任务提示见 [`docs/NEXT_CODEX_PROMPT.md`](docs/NEXT_CODEX_PROMPT.md)，可直接复制。已有 checkout 时先查看 `git status`，确认没有未保存修改再 `git pull --ff-only`。

## 记录入口

| 文件 | 内容 |
|---|---|
| [H800_CODEX_HANDOFF.md](docs/H800_CODEX_HANDOFF.md) | 当前状态、接续顺序、操作边界、必做实验与产物 |
| [WORK_LOG.md](docs/WORK_LOG.md) | 已完成的真实工作、部署决策、修复与未完成事项 |
| [EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md) | 原始日志、完整中图答案、校验值和证据范围 |
| [ACCEPTANCE.md](docs/ACCEPTANCE.md) | 完成判据与最后提交检查 |
| [ASSIGNMENT_REQUIREMENTS.md](docs/ASSIGNMENT_REQUIREMENTS.md) | 题目要求摘要、与实验室方案的差异 |

代码和实验命令在 [`homework1/`](homework1/README.md)。历史报告 Markdown/PDF 已保留，环境段落和 `NOT MEASURED` 字段须用真实实验补完，不能直接当作最终报告。

原始课程图数据、Shakespeare 文本和 Yelp 原文件不放入 Git；获取地址、原始输入 manifest 和哈希均已记录。压缩的既有结果及 28 份真实本地 Hadoop 日志已纳入仓库，便于核查，**它们不是本次四机实验结果**。

```bash
python3 scripts/verify_repository.py
cd homework1
python3 -m unittest discover -s tests -v
```
