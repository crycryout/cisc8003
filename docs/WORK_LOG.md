# 工作记录与交接状态

此文件记录实际工作和决策；“准备好”不等于“已经在实验室运行”。后续 agent 请按日期追加真实命令、结果和证据路径。

## 2026-11-03：原题分析和真实本地执行

1. 完成 Hadoop 3.3.6 / JDK 11 的单节点与四节点配置说明，Q1 WordCount/参数扫描/JobHistory 采集，Q2 六阶段精确算法、独立 oracle 与报告草稿。
2. 从原题 Dropbox 中图 URL 取得真实输入：2,420,766 行、1,768,149 唯一有向边、81,306 用户，识别二列边表和重复边。SNAP 官方说明支持第一列 follower 的解释。
3. 用真正的 Hadoop LocalJobRunner 跑完图例、额外回归和中图各六个 Streaming jobs，另跑内置 WordCount；修复 Streaming combiner 复合 key 属性和数值排序/输出细节。中图最终 81,306 行，1000 个独立抽样重算无差异；全部 suffix 曾导出。
4. 从原题 Shakespeare URL 准备 196 个文本和 6,460,189-byte merged 输入，在真实本地 Hadoop 下得到相同的 72,379 个 token 词频。同期有其他验证作业，因此不宣称这些日志给出有效对照性能。
5. 从 Yelp 官方公开 ZIP 完整下载并提取 5,341,868,833-byte review JSONL，保存 manifest。曾准备腾讯云 2核4GB lowmem 档和总入口；云登录未完成，没有创建 VM、付款或云性能结果。大图 bonus 未运行。

历史代码通过 13 项测试；随后 lowmem 六阶段真实本地回归成功。完整运行日志、counters、状态和结果均可在本仓库核查。原始运行框架是 local file:// + LocalJobRunner，不是 YARN 四机或课程 IE DIC。

## 2026-11-06：恢复材料与改用实验室

1. 从此前交付的当前版本工作包恢复代码和已有结果。大体积 Yelp 原文件与临时 Hadoop runtime 已不在当前工作目录；保留下载记录不能替代文件本身，须重新获取。
2. 用户决定不再用云，改用 H800 NUMA 双节点主机和两台独立 5090。最初讨论过三台物理机 master/worker 同机；用户补充独立 Jetson Thor 后，最终改为**四台物理机、Thor 独立 master、另三台 workers**。不再采用三机共置或 NUMA 伪装四主机方案。
3. 核实 Apache 3.3.6 官方归档包含 aarch64 包，安装脚本自动按架构选择并校验 SHA-512；默认不安装 OS 依赖。配置从各机本地环境读取 JDK/Hadoop 路径，避免 ARM64 master 的路径写死到 x86 workers。
4. `run_required.sh` 支持 standard / lowmem，结果目录去掉腾讯云命名，增加 REPETITIONS；补充只读 preflight 和实验室部署文档，修复 0 值资源额度被静默替换的问题。
5. 15 项单元测试通过；shell 语法、预检 JSON 和两种架构的模拟选择检查通过。**没有实验室主机访问，没有 ARM64 实机启动，没有四机测试**。这些检查的范围记于 `homework1/results/lab_preparation.json`。

## 2026-11-06：GitHub 接续

用户明确指定 `crycryout/cisc8003` 作为记录和执行交接仓库，由 H800 上的 Codex 拉取继续。开始时检查到该仓库为空、默认 main、public，并有 push 权限。

本次整理代码、当前部署指南、历史报告与记录、真实验证摘要、28 份压缩原始日志、压缩全量中图结果、压缩 Shakespeare 参考词频；原始课程图/Yelp/Shakespeare 文本不提交。提供 AGENTS、完整接续说明、任务提示、验收清单、证据索引和内容哈希检查。原 ZIP 中 1,000 个 suffix 文件可由仓库中的完整答案重新导出，不重复提交。

H800 agent 的首要动作是核对 checkout、运行测试、采集本机预检并确认另外三台访问。尚缺真实主机访问信息、正式集群证据、Q1 时间表和 bonus；不需要再回到云登录流程。

## 后续实际实验追加格式

每一阶段记录：日期/实际主机与资源（公开版脱敏）、执行命令、输入/配置哈希、输出根/run ID、job ID、退出状态、验证、证据路径、下一步。失败也保留日志；不要将计划条目改写成已完成。
