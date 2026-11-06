# 复制给 H800 上 Codex 的任务

你现在在我的 H800 服务器上。我已把之前准备的 Hadoop 作业代码、历史结果和详细接续记录放入当前仓库。请先完整读取根目录 AGENTS.md、docs/H800_CODEX_HANDOFF.md、docs/WORK_LOG.md、docs/EVIDENCE_INDEX.md 和 docs/ACCEPTANCE.md，然后直接接续完成必做实验，不只给我方案。

部署使用实验室的四台独立物理主机：Jetson Thor 做 master；H800 主机、两台单机 RTX 5090 各做一个 worker。H800 的两个 NUMA 节点不拆分；不租云服务器。先检查当前机器和本账号的实际资源、现有端口/服务以及现有 SSH 主机别名，再确认另外三台的可达性。不要读取或输出私钥、口令、token。若缺少实际地址或权限，先完成所有不受阻塞的本地准备，再只向我询问缺少的信息。

你需要完成单节点验证、1 master + 3 workers 的 HDFS/YARN 集群、Shakespeare 小文件与合并文件 WordCount、Yelp 至少四种不同实际 mapper/reducer 组合、Q2 中图六阶段精确 Top-10、完整性与独立抽样验证、suffix 导出、真实截图/原始日志/JobHistory 和最终报告。大图 bonus 先评估容量，不能以必做结果冒充 bonus。

继续复用仓库中已修复并验证的实现。历史结果属于 LocalJobRunner，不是四机性能；所有耗时从真实成功作业采集，未完成的保持 NOT MEASURED。先跑一轮完整链路；时间和资源允许时将 Q1 每组补到三次并保留所有运行。若缺 SID 后三位先导出全部 suffix，不要为此停下实验。

不要修改 CUDA、GPU 驱动、系统默认 Java，也不要干扰其他人的作业或重新 format 既有 HDFS。使用本次独立目录和新输出路径，保留失败日志。每完成一阶段更新 docs/WORK_LOG.md、docs/ACCEPTANCE.md 和对应证据索引；将可公开的代码、汇总和最终报告提交到当前仓库，机器访问配置和私密信息保留本地。
