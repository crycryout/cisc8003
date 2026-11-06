> 历史接续文档：2026-11-06 已在四台真实物理机执行。当前进展和证据以 [LAB_EXECUTION.md](LAB_EXECUTION.md)、[WORK_LOG.md](WORK_LOG.md) 和 [ACCEPTANCE.md](ACCEPTANCE.md) 为准；不要据此重新 format 或覆盖已有结果。

# 给 H800 上 Codex 的完整接续说明

记录截至 2026-11-06。用户决定让 H800 上的 Codex 从本仓库接续并实际完成实验。当前对话的执行环境没有实验室内网访问，**没有连接四台机器、没有启动实验室 Hadoop，也没有集群性能数据**。

## 1. 任务与当前状态

目标是完成 Homework 1 的部署、Q1 实测、Q2 中图集群执行、验证、截图和最终报告，不是重新实现已经验证的算法。

| 项目 | 已完成 | 仍需完成 |
|---|---|---|
| 软件/算法 | Hadoop 3.3.6 / Java 11 本地真实运行；六阶段精确 Top-10 | 在真实四机 YARN 上验证 |
| Q1(a) | 配置生成、smoke 命令 | 四台各自单节点运行和截图 |
| Q1(b) | Shakespeare 两种输入在本地 Hadoop 的输出一致 | 四机小文件/合并文件实测和截图 |
| Q1(c) | 四组 M/R 扫描、History 采集、真实 Yelp manifest | 重新取得原文件并运行实际参数对照 |
| Q2 | 中图全部 81,306 个用户结果、独立抽样 1,000 个零误差 | 本次集群重跑、比对、证据和 suffix 输出 |

大图 bonus 未运行。截止日原题写 2026-11-09 23:59，未注明时区，以课程平台为准。`report/` 是旧的英文草稿，不得直接将其中云环境描述当作本次事实。

## 2. 已确定与未确定的部署信息

用户已决定使用四台独立物理机器，取代此前云方案：

| 机器 | 服务 | 备注 |
|---|---|---|
| Jetson Thor | NN、SecondaryNN、RM、JobHistory | 独立 master；ARM64 安装路径已准备，仍须 uname 验证 |
| H800 主机 | DataNode、NodeManager | 一个 worker；NUMA 两节点不拆成两台 |
| 5090 主机 A | DataNode、NodeManager | 一个 worker，实际 CPU 架构待查 |
| 5090 主机 B | DataNode、NodeManager | 一个 worker，实际 CPU 架构待查 |

主机 IP、SSH 端口/用户、已有别名、可用磁盘、当前负载和端口冲突都未知。`thor/h800/rtx5090a/rtx5090b` 是示例，不能当作真实 DNS。先检查 H800 本地和用户已有的 SSH 连接元数据；不要读取私钥、搜索 token 或把登录配置提交 Git。

三个 workers 使用统一的起始资源额度：standard 档 6144 MiB YARN 内存、4 vcores；map/reduce 各 1536 MiB、Java heap 768 MiB；AM 1536 MiB / heap 1024 MiB。实际启用前确认各机至少有这些**可供本次任务使用**的资源并留 OS/守护进程余量。GPU 型号不能代替 CPU/RAM 信息，YARN 默认 vcores 额度也不等于硬件 CPU 隔离。

## 3. 先做本地验证和四机预检

从仓库根目录执行：

```bash
python3 scripts/verify_repository.py
cd homework1
python3 -m unittest discover -s tests -v
python3 cluster/lab_preflight.py --work-dir "$HOME"
bash cluster/bootstrap_node.sh --plan
```

本次上传前 15 项单元测试通过；两种架构的 `--plan` 分支只做了模拟 uname 的选择检查，**不是 ARM64 上的实际启动验证**。预检程序在每台真实主机各执行一次，输出保存到仓库忽略的 `/.local/`，再整理可公开的环境摘要。若实验目录另有 SSD，预检指向该盘上已有目录。

优先解决真实可达性、端口和工作盘，再安装。不要为跑作业改 CUDA/驱动/系统默认 Java；Hadoop 与 JDK 可位于本次账号目录。`bootstrap_node.sh` 默认不 apt 安装，缺 JDK 11 时退出。Thor 若仓库没有 JDK 11 包，使用验证过的 ARM64 用户目录 JDK；不要默认 apt 一定可行。已有 `~/hadoop-3.3.6` 或 `~/hadoop-env-user.sh` 时先确认归属与内容，不能覆盖其他项目环境。

## 4. 数据来源与可复现检查

### 中图

```bash
cd homework1
python3 src/fetch_course_data.py medium --decompress
```

若已在 homework1 目录，不要重复 `cd`。脚本拒绝覆盖现有文件；已存在的输入先核对哈希，再复用。

| 属性 | 原来实际观察值 |
|---|---|
| 原题 URL | https://www.dropbox.com/s/g1nthvj98iaikly/twitter_combined.txt.gz?dl=1 |
| gzip 大小 | 10,621,918 bytes |
| gzip SHA-256 | `d9f99b0e6a53b9204b8c215f41b3c10fb99a1e1e783858c012b06d0d3d4bd129` |
| 输入行 / 唯一有向边 / 用户数 | 2,420,766 / 1,768,149 / 81,306 |
| 格式与方向 | 二列边表，第一列 follower，第二列 followee |
| 最大 followers / 配对贡献数 | 3,383 / 154,933,408 |

原题文本的规模描述与真实下载不一致，已有记录解释；以原题 URL 实际返回内容为准，不能用其他同名下载静默替换。SNAP 的 `readme-Ego.txt` 定义 a b 为 a follows b；见原记录 `results/data_access_status.json`。

### Shakespeare

`python3 src/fetch_course_data.py shakespeare` 使用原题 URL：

`https://github.com/hupili/agile-ir/raw/master/data/Shakespeare.tar.gz`

检查 archive 成员，安全提取到独立目录，仅选择文本目录，交给 `prepare_words.py`。原先规范化后是 196 个文件、merged 6,460,189 bytes；参考 manifest 已保留。非空文件末尾补换行，两种条件共享相同 token 流。准备好的实际输入必须位于总入口期望的 `data/shakespeare_prepared/small` 和 `merged.txt`，或显式修改本次路径。Git 中仅有参考 manifest，**没有原始文本**。

### Yelp

| 属性 | 记录 |
|---|---|
| 官方页 | https://business.yelp.com/data/resources/open-dataset/ |
| 官方公开 ZIP | https://business.yelp.com/external-assets/files/Yelp-JSON.zip |
| 原来 ZIP 大小 | 4,345,335,132 bytes |
| 原来 review JSONL 大小 | 5,341,868,833 bytes |
| review SHA-256 | `a4edc050d14eec25373a75e7ee211d42f49f14f47230837d8c7849eb9c5f2f96` |

Nov 3 曾完整下载并提取，当前大文件已不在工作目录/代码包中，须在服务器重新取得。ZIP 的 `Yelp JSON/yelp_dataset.tar` **实际是 gzip**，可用 Python `tarfile.open(fileobj=..., mode="r|*")` 流式识别，只提取目标 review JSONL；注意工作盘空间。

使用完整未压缩 review JSONL 当文本，不抽样、不重复扩增、不将 gzip 直接用于可分片 M/R 对照。若课程要求只统计评论 text 字段，先一致转换并重新记录派生文件哈希。官方文件如已更新，以新实际数据和 manifest 为准，四种配置必须使用同一份输入。

## 5. 部署与必做实验顺序

详细命令见 `homework1/cluster/LAB_E2E.md`。先每台分别做伪分布式 WordCount smoke test，截图后停止本次服务，再切换到新的 multi 目录。只对确认全新的空 NameNode 目录 format 一次。

ARM64 master 与 x86 workers 的 JDK 路径不同，不能复制整个 x86 安装目录到 Thor。每台本地安装、生成配置、解析本机 `hadoop-env-user.sh`。逐节点启动 daemons，避免不同用户名/HOME 导致 `start-dfs.sh` 的远程路径假设失败。若不同 SSH 账号，需要核对本次 HDFS/YARN 目录权限。

集群验收必须看到 3 live DataNodes、3 RUNNING NodeManagers，Thor 仅运行管理服务。再运行跨节点 smoke test，确认 History 正常返回成功 job 的任务数据，才开始计时。

| 阶段 | 运行 | 完成判据 |
|---|---|---|
| Q1(b) | 相同 WordCount，小文件与 merged | 保留实际 maps/reducers；词频完全一致 |
| Q1(c) | Yelp `6:1,6:3,12:1,12:3` | 至少四种不同**实际** M/R 组合；七项时间完整；输出一致 |
| Q2 中图 | `edges follower-followee` 六阶段 | 六 jobs 成功；全体用户输出；独立验证和参考比对 |
| 报告 | 真实环境、表格、图与解释 | 不留必做项 NOT MEASURED，不把本地历史日志写成四机实测 |

先跑一次完整链路；正式 Q1 可补到每组 3 次，保留每次 job ID/原始时间，不只选最快值。`run_required.sh` 支持 `REPETITIONS`，默认 1；若要先检查 Q2 容量，按分步命令跑 Q1/Q2，避免总入口再次重复整轮。

上传真实输入 HDFS 后的总入口：

```bash
source "$HOME/hadoop-env-user.sh"
source generated-lab/homework-env.sh
REPETITIONS=1 bash cluster/run_required.sh \
  /hw1/input/yelp/reviews.json /hw1/input/community/medium.txt
```

Q2 可先 `STOP_AFTER_BLOCKS=1` 执行到 stage 03，检查 CandidatePairs、可用盘和数据规模；再以相同输入/输出根使用 `RESUME_AFTER_BLOCKS=1` 继续。不要根据 10 MB 压缩图体积估计整个配对阶段。大图 bonus 也必须先检查，不能承诺一定能跑完。

## 6. 不要回退的正确性修复

1. jobs 01/05 设置 `stream.num.reduce.output.key.fields=3`，保证 combiner 保留整个复合 key；不要改成错误的属性名。
2. job 06 按 `(u,-score,v)` 做数值 secondary sort，partition 只用 u，输出 `user:id id ...`。ID 是任意精度非负整数，不用浮点排序替代。
3. 先去重边，再计算所有用户的共同 followee 计数；平分时按数字 ID 升序，缺正分候选时补零分。不能变成共同 follower、Jaccard 或只算某个 suffix 子图。
4. `metrics.py` 从已完成的 JobHistory jobs/tasks/counters 提取数据；reduce 时间包含 shuffle+sort+reduce。task 时间并行重叠，不能把 task 时间相加作为 job 时间。
5. 原始完整答案的字节 SHA 受 part 文件合并顺序影响。新集群 reducers 数不同，不能只用旧的 raw SHA 判错；应按用户和候选顺序比较内容。

## 7. 验证、保存与最后交付

先在本次独立输出目录合并集群结果，再执行：

```bash
python3 src/validate_medium.py --input data/course_medium.txt.gz \
  --results results/lab-RUN/medium_all_users_top10.txt \
  --output results/lab-RUN/medium_validation.json --samples 1000
python3 ../scripts/compare_top10.py \
  --reference artifacts/medium_all_users_top10.txt.gz \
  --actual results/lab-RUN/medium_all_users_top10.txt \
  --output results/lab-RUN/reference_comparison.json
python3 src/export_suffixes.py --input results/lab-RUN/medium_all_users_top10.txt \
  --output results/lab-RUN/medium_by_suffix
```

`RUN` 需替换为本次真实 run ID，目录先创建；不要对字面占位符声称已经执行。先对所有用户计算后再筛选 SID 后三位。用户尚未提供末三位，因此导出全部 1,000 个 suffix 即可；不要索要完整 SID 才肯继续。

保存四机环境摘要、配置、命令/退出码、输入大小与哈希、所有实际 job IDs、原始 History JSON、CSV、counter、全量结果、验证和真实截图。私密 IP/SSH 等留在 `.local/`，公开摘要/经过检查的截图再提交。当前仓库是 public，不上传私钥、token、账号信息、原始 Yelp 或无关实验室数据。

用这些事实更新 `report/Homework1_Report_Draft.md`，再生成并视觉检查 PDF，确保表格可读、没有截断、环境与实际一致。保留 AI 协助和引用说明；姓名/SID/原创声明/签名由用户本人核实填写。最终更新 WORK_LOG、ACCEPTANCE、EVIDENCE_INDEX，提交明确的 commit 并报告完成/未完成项目。
