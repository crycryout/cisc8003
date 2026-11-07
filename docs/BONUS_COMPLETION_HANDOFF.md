# Homework 1：补完大图加分题与最终提交包

更新时间：2026-11-07。对象：在 H800 上工作的 Codex，可通过用户已有连接访问 Thor 和两台 5090 主机。

## 直接执行的任务

用户已授权补完尚未完成的作业工作。请完成 **Q2(b) 大图精确全用户 Top-10、独立验证、学号后缀导出、证据、报告和提交包**，不要只回复计划。先读取本文件，再按根目录 `AGENTS.md` 和当前实测记录执行。正常的代码修复、隔离目录操作、既有四机计算和仓库同步直接继续；仅在确实缺少访问权限、数据或无法获得足够资源时报告具体阻塞，并先完成不受阻塞的工作。

本文件是新一轮接续入口，不代表 bonus 已经运行。编写时核对的远端基线为 `b6670cc6b0d1b43759ceae3969caa2a3de9c12bc`。旧 `H800_CODEX_HANDOFF.md` 中“必做实验未执行”的表格是历史状态，不能据此重做已完成实验。

## 1. 确认当前状态并复用集群

### 已完成与剩余

| 项目 | 真实状态 | 本轮处理 |
|---|---|---|
| Q1(a)/(b)/(c) | 四机单节点、Shakespeare 各三次、完整 Yelp 四组各三次已完成 | 保留全部结果与计时，不重新跑整套 |
| Q2(a) | 中图六阶段成功，81,306 用户，1,000 独立抽样与全量参考比对零差异 | 保留作为回归依据，不冒充大图 |
| Q2(b)，15 分 bonus | 未运行课程 Ref[8] 的大图 | 本轮主要计算任务 |
| 报告和结果 | 24 页 PDF、中图全量与 000–999 后缀归档已有 | 增补真实 bonus 并制作提交包 |
| 个人与课程事项 | 姓名/SID/声明/签名待本人核实；实验室替代云 VM 与 AI 协助已披露 | 保留披露，生成待本人处理清单，不代签或虚构教师批准 |

先读 `docs/LAB_EXECUTION.md`、`docs/WORK_LOG.md`、`docs/ACCEPTANCE.md` 和 `docs/EVIDENCE_INDEX.md`。旧证据根为 `homework1/evidence/lab-20261106T110350Z/`；本轮不得覆盖它。

从已有 checkout 根目录开始：

```bash
git status --short
git log -3 --oneline
python3 scripts/verify_repository.py
python3 -m unittest discover -s homework1/tests -v
```

先保护服务器上未提交的工作，再正常同步远端；不要 `reset --hard` 或覆盖本地配置。字节校验失败先解释具体变更，不能直接重写清单掩盖意外损坏。

复用 **Thor master + H800/两台 5090 workers**，H800 的两个 NUMA 节点仍是一个 worker，GPU 不参与计算。通过现有私密 SSH 配置和 `.local/` 记录找回实际连接，不把示例名当 DNS，不读取或展示密钥内容。下述 Hadoop 命令在已配置且验证能访问本次集群的提交节点执行，优先 Thor；H800 若缺相同的 client 配置，就通过现有 SSH 到 Thor 执行。

```bash
# 在对应 checkout 根目录；这是已有实验配置，不是安装目录的默认配置。
source .local/conf/multi/homework-env.sh
hdfs dfsadmin -report
yarn node -list
```

验收为 3 Live DataNode、3 RUNNING NodeManager 和可访问的 JobHistory。若本次服务已停，只恢复本次独立目录内的服务。**不要调用 `lab_node.sh ... start-master`：它是初始化入口，会进入 format 检查并在已有目录时退出。** 先核对本次配置/PID/进程，只启动缺失的本次 daemon：Thor 上使用 `hdfs --daemon start namenode`、`hdfs --daemon start secondarynamenode`、`yarn --daemon start resourcemanager`、`mapred --daemon start historyserver`；workers 上分别检查 `datanode`/`nodemanager`，缺失时在各自原配置下启动。不要重复启动已存在进程、重新 format NameNode、停止他人服务或改变系统 Java/CUDA/驱动。不要为 bonus 租云、购买磁盘或扩大到其他账号资源。

**单独验证 Python 能访问 History REST。** 既有 JVM hosts 文件只影响 Java；`HW1_HISTORY_URL=http://master:39888` 即使对 Hadoop 有效，Python urllib 也可能无法解析 `master`。Thor 本机确认端口/绑定后可改为 `http://127.0.0.1:39888`；其他节点用私密 inventory 中实际可达的地址或现有隧道，不修改系统 DNS。用 Python 请求 `/ws/v1/history/info` 验证后再采集，真实访问地址只留本地。

## 2. 获取并识别课程大图

必须先尝试原题 Ref[8]，仓库已有下载入口：

```bash
python3 homework1/src/fetch_course_data.py large \
  --directory homework1/data --decompress
```

实际课程 URL 为 `https://www.dropbox.com/s/cbf4r2at8dmd9ms/gplus_combined.txt.gz?dl=1`。默认落地为 `homework1/data/course_large.txt.gz`、`course_large.txt` 和 gzip metadata。文件已存在时下载器会拒绝覆盖：核对元数据、gzip 完整性和哈希后直接复用。中断下载可能留半文件；隔离失败副本后续传或重下，不能把“文件存在”当下载成功。

先检查 gzip/解压完整性、实际格式、边方向和输入内容，再计算压缩/解压后字节与 SHA-256。用流式或磁盘辅助方式记录非空行数、唯一有向边数、全部 endpoint 用户数、重复边与入度分布；不得根据题面约 480 万用户填写统计。

| 实际格式 | runner 的第 3 个参数 | 第 4 个参数 |
|---|---|---|
| 二列边表，第一列 follower | `edges` | `follower-followee` |
| 二列边表，第一列 followee | `edges` | `followee-follower` |
| `followee:follower follower ...` | `adjacency` | 参数仍需记录，边方向由格式决定 |

不能靠 `auto` 格式识别推断边方向。保留原题数据来源、重定向和方向依据；不要启用 `UNDIRECTED=1`。原链接不可访问时先检查重定向与重试；如不得不使用公开镜像，明确标为替代来源并记录内容核验，不能声称原题数据已验证。没有原题数据或足够等价证据时，bonus 的输入资格保持未确认。

## 3. 执行前三阶段并检查容量

使用独立 run ID。以下变量在确认 client 配置的同一个 shell 中建立；跨节点/断开重连时，从本轮私密状态文件恢复，不重新生成而混用路径。

```bash
export BONUS_RUN="bonus-$(date -u +%Y%m%dT%H%M%SZ)"
export BONUS_EVIDENCE="$PWD/homework1/results/lab-$BONUS_RUN"
export BONUS_LOGS="$BONUS_EVIDENCE/community-logs"
export BONUS_INPUT="/hw1/input/community/$BONUS_RUN/large.txt"
export BONUS_OUT="/hw1/$BONUS_RUN/community"
export BONUS_FORMAT=edges
export BONUS_EDGE_ORDER=follower-followee
export REDUCERS=6 BLOCK_SIZE=512 K=10 HW1_MEMORY_PROFILE=standard
mkdir -p "$BONUS_EVIDENCE" "$BONUS_LOGS"
```

`BONUS_FORMAT` / `BONUS_EDGE_ORDER` 必须依据第 2 节实际观察修改；此处默认值只适用于确认过方向的二列边表。保留本次变量、代码 commit、配置哈希和输入哈希到私密状态文件。若已有本轮运行，恢复状态而非新建路径或覆盖。

先记录三台 workers 与 master 的工作盘剩余空间、HDFS 总量/剩余量、复制因子、YARN local/log 目录和当前负载。确认本轮输入/输出不存在后执行：

```bash
hdfs dfs -mkdir -p "${BONUS_INPUT%/*}"
hdfs dfs -put homework1/data/course_large.txt "$BONUS_INPUT"
LOG_DIR="$BONUS_LOGS" STOP_AFTER_BLOCKS=1 \
  bash homework1/src/run_community.sh \
  "$BONUS_INPUT" "$BONUS_OUT" "$BONUS_FORMAT" "$BONUS_EDGE_ORDER"
```

保留 `01_dedup`、`02_universe`、`03_blocks` 的成功 JobHistory、counters 与原始日志。`03_blocks.log` 中取出的真实 job ID 可用以下实际 CLI 采集；`STAGE03_JOB` 需由日志解析并校验为本轮唯一 ID：

```bash
python3 homework1/src/metrics.py \
  --base-url "$HW1_HISTORY_URL" --job-id "$STAGE03_JOB" \
  --output "$BONUS_EVIDENCE/capacity-history/03_blocks"
```

从 HW counters 读取 `Users`、`Edges`、`CandidatePairs`、`ReplicatedFollowerIDs`。CandidatePairs 为 `sum_f d_f*(d_f-1)/2`，小压缩输入仍可能产生极大中间结果；分块只改善内存界限，不消除精确枚举量。

容量判断必须写出数值和假设，至少分开考虑：HDFS 中间结果及副本、各 worker shuffle/spill、数据倾斜/并发/重试峰值、验证与最终输出。参考已保存中图 counters 的真实吞吐和每 pair 字节估计区间；不能把中图的“100 GiB 空闲”或“256 bytes/pair”当通用保证或上界。题面“约十小时”也不是本机实测预测。

容量通过后自动继续。暂不足时先在已授权资源内调整 reducer 数、分块、压缩和独立工作盘；不能清理旧作业证据/他人数据来腾空间。改 `BLOCK_SIZE` 必须在独立准备输出根重建 stage03，仅改变量后 resume 不会改变已有分块；改 reducer 数须记录各阶段的实际配置。若必须修改算法，只能使用有正确性依据的精确方案，并先通过回归和独立验证，不能改为近似 Top-10、只算 SID 用户或抽样冒充全图。确实无法容纳时保存容量证据、还缺多少资源、已尝试方案和恢复点，再报告阻塞。

## 4. 完成全图精确 Top-10

确认参数、stage01–03 的 `_SUCCESS`、日志和输入哈希一致后继续。不要同时设置 `STOP_AFTER_BLOCKS=1`：

```bash
LOG_DIR="$BONUS_LOGS" RESUME_AFTER_BLOCKS=1 \
  bash homework1/src/run_community.sh \
  "$BONUS_INPUT" "$BONUS_OUT" "$BONUS_FORMAT" "$BONUS_EDGE_ORDER"
```

保留同一 `BONUS_LOGS` 中六个 stage 日志。监控各节点可用盘、YARN 作业/attempt、shuffle/spill、进程内存和倾斜 reducer；定期写入进度，断开会话后也应能判断当前是否仍有作业运行，避免重复提交。保留所有失败尝试的证据。

**现有 runner 的恢复边界：** `RESUME_AFTER_BLOCKS=1` 只恢复前三阶段，且会拒绝已经存在的 `04_pairs`、`05_scores` 或 `06_top10`。阶段 4–6 中途失败时，先核实活动 jobs，再为 runner 实现明确的“从指定成功阶段继续”能力，或在独立恢复根复用完整上游产物。不要盲目重试同一命令、删除成功中间结果，或把失败输出当成功输入。runner 使用 `tee` 覆盖同名阶段日志，重试前将失败日志及 job IDs 归档到六阶段日志目录之外，再保存本次成功阶段日志。代码修复须在所有实际提交节点同步，并记录版本。

所有六阶段成功后：

```bash
python3 homework1/cluster/collect_community_metrics.py \
  --logs "$BONUS_LOGS" --output "$BONUS_EVIDENCE/history"
hdfs dfs -getmerge "$BONUS_OUT/06_top10/part-*" \
  "$BONUS_EVIDENCE/large_all_users_top10.txt"
```

采集器要求 logs 目录恰好六个 `.log`，不要把监控日志也放进去；output 必须是新目录。不要用 LocalJobRunner、计时估算或中图 jobs 填充大图表。

保留精确语义：共同 followee 数、先去重边、排除自身、同分按数值 ID 升序、缺正分候选时按既定规则补零分；所有 endpoint 与空邻接 head 均属于用户集合。jobs 01/05 保留 `stream.num.reduce.output.key.fields=3`；job 06 保留数值 secondary sort 和按用户分区。大整数 ID 不转浮点。

## 5. 验证并导出全部后缀

**不要未经内存评估直接对大图运行 `validate_medium.py`。** 它把双向邻接、全量排名加载进 Python 内存，还会整体读结果计算哈希。现有 `export_suffixes.py` 也把全部输出累积在内存。请在服务器实现并测试流式/磁盘辅助的大图验证与后缀导出；可用 SQLite、外部排序或紧凑数组，不要求新装大型依赖。

| 验证层 | 必须保存的证据 |
|---|---|
| 全用户覆盖 | 从原始输入独立构造用户集合；输出无遗漏、多余或重复用户，不能只比行数 |
| 输出合法性 | 每用户 `min(10,N-1)` 个不同且非自身的存在候选，格式和任意精度 ID 正确 |
| 独立精确排名 | 至少 1,000 固定种子用户，另加高入/出度、零正分、边界 ID 等定向样本；从原始边独立去重重算 Top-10 |
| 后缀分区 | 完整计算后流式分为 `000.txt`–`999.txt`，核验每行 `int(user_id)%1000`，总行数和用户集合一致 |
| 完整性 | 流式 SHA-256、字节数、样本 seed/IDs、验证器版本、失败/差异数和归档清单 |

验证器不得 import `community.py` 的排名逻辑作为唯一 oracle；独立处理格式、边方向、重复边和零分补齐。为新验证器加入小图随机/边界测试，并利用已有中图结果回归。输入去重的磁盘索引应保留所有 endpoint；只出现为 followee 的用户也要覆盖。

如果内存足够，也可采用经过测量的内存验证，但必须记录内存预算和峰值，不因名字叫 large 就假定一定 OOM。没有独立全量参考时如实写“全量覆盖/格式检查 + 独立精确抽样”，不能写“全用户排名均已独立验证”。

导出全部 1,000 个后缀文件，不等待完整学号。若用户之后提供末三位，再额外选出对应文件；不代填完整 SID。全量大图结果与后缀归档保存于用户可访问的服务器交付目录；公开 Git 中只提交体积合适且符合课程数据使用约定的派生产物。超过托管单文件限制时使用合法的制品存储或压缩分卷并提供真实路径、manifest；不要承诺巨大文件已推送成功。

## 6. 更新报告、提交包和仓库

保留原 24 页报告与旧证据的可追溯版本，再更新 `homework1/report/Homework1_Report_Draft.md`，增补大图输入实测规模/方向、算法和容量决策、六 job IDs/实际时间、资源峰值、验证、后缀位置和实际截图。封面、完成状态、日期和 bonus 章节必须一致；不能只删“未完成”而无结果证据。Q1 表与中图历史值不变。

```bash
python3 homework1/report/build_report.py \
  --input homework1/report/Homework1_Report_Draft.md \
  --output homework1/report/Homework1_Report.pdf
```

渲染并检查 PDF 的新增页、结果表和截图。构建脚本页脚当前硬编码 `6 Nov 2026`，应根据本轮实际日期更新或参数化；同时处理仍使用旧 PDF 的 `Homework1_Report_Draft.pdf`，不得留两个互相矛盾的“最终版”。若缺 reportlab/字体，使用本账号环境或已有环境，不更改系统默认依赖。截图必须来自真实终端或 Hadoop 服务页，并遮蔽访问标识。

完成后更新以下交付内容：

| 内容 | 位置/要求 |
|---|---|
| 实验与验收记录 | 追加 `WORK_LOG.md`，更新 `ACCEPTANCE.md`、`LAB_EXECUTION.md`、`EVIDENCE_INDEX.md`、README 的真实状态 |
| 本轮公开证据 | 新建 `homework1/evidence/lab-$BONUS_RUN/`，整理脱敏 JobHistory、counters、CSV、输入/输出 manifest、验证摘要与截图 |
| 可提交代码包 | mapper/reducer/runner、必要辅助脚本、运行说明、最终报告；不含原始图/Yelp、巨大中间结果和机器访问配置 |
| 用户结果包 | 中图及大图后缀归档/选定 SID 文件、校验清单、明确的本地交付路径；全量结果另留可访问归档 |
| 最后人工清单 | 姓名/SID/日期、本人签名与声明、实际讨论者/来源、课程对实验室替代与 AI 协助的适用要求 |

不要代写本人确认、代签声明、虚构教师认可或删去 AI 协助披露；这些不是计算任务，无法由服务器 Codex 替用户完成。无需为此暂停其他实验或要求用户先给出完整 SID，也不要自动给老师发邮件。

注意：旧 `evidence/lab-20261106T110350Z/input-manifest.json` 是早期快照，Yelp 当时还在下载；最终状态见同 run 的 `yelp-input-manifest.json`。本轮引用最终文件并解释旧快照，不把它误报为“Yelp 未完成”，不改写旧原始证据。

最后运行相关单元/回归测试、shell 语法检查、`git diff --check`、产物哈希与公开内容检查。`docs/IMPORT_MANIFEST.json` 对有意修改的文件透明更新 bytes/SHA-256 并纳入新代码/文档，保留 `base_import_commit`；不得把快照校验说成实验验证。确认没有凭据、SSH inventory、私网访问配置或原始大数据后，提交并同步当前仓库；若远端已有新提交，正常整合，不 force push。中途先保存检查点，不能等全部大图跑完才记录进度。

最终中文汇报只需给出：完成/未完成表、bonus 实际数据规模与六个 job IDs、验证范围/结果、报告/代码/结果包路径、commit，以及必须由学生本人处理的项目。若未完成，明确当前阶段、真实失败原因和精确恢复命令；不要把准备工作写成 bonus 完成。
