# Homework 1：解题与运行包

**代码、解题分析及 Q2 中等数据集的本地完整计算已完成；现按用户决定，改用实验室四台物理机，集群实测、截图与 Yelp 性能表仍待补齐，大数据 bonus 未运行。**

当前拓扑（2026-11-06）：**Jetson Thor 做 master，H800 主机和两台 RTX 5090 主机各做一个 worker**。当前部署入口为 `cluster/LAB_E2E.md`，含只读环境检查与 ARM64/x86_64 安装适配。尚未连接这些主机，也未产生四机实测结果。下文云方案为历史准备；现有 PDF 是待实测后更新环境与表格的旧草稿。

截止时间：原题为 **2026-11-09 23:59**；题面没有注明时区，请以课程平台为准。

## 1. 现在先看什么

| 文件 | 用途 |
|---|---|
| `report/Homework1_Report_Draft.pdf` | 英文报告草稿：解题、正确性证明、实验方法、待补实测表 |
| `report/Homework1_Report_Draft.md` | 同内容的可编辑文本 |
| `cluster/LAB_E2E.md` | 当前四台实验室主机的拓扑、架构检查、部署与运行步骤 |
| `cluster/DEPLOYMENT.md` | 原云部署步骤，单节点 smoke test 可继续参考 |
| `src/run_wordcount.py` | Q1：比较小文件/合并文件，扫描至少 4 组 mapper/reducer，自动采集耗时 |
| `src/run_community.sh` | Q2：6 个 Hadoop Streaming 作业，计算每个用户的精确 Top-10 |

## 原腾讯云方案（已改用实验室设备）

已加入 2核4GB 节点的低内存配置 `--profile lowmem`，以及必做实验总入口 `cluster/run_required.sh`。具体分工和操作见 `cluster/TENCENT_E2E.md`。低内存档已通过 6 个真实 Hadoop 本地阶段的回归检查；四台 CVM 尚未创建和验证。

原题 [7] 的压缩输入已附在 `data/course_medium.txt.gz`，可解压后直接上传集群。无需再次从 Dropbox 下载。解压命令：`gzip -dc data/course_medium.txt.gz > data/course_medium.txt`。

## 已完成的中等数据集结果

| 文件 | 实际内容 |
|---|---|
| `results/medium_all_users_top10.txt` | 全部 81,306 个用户，每人 10 个候选 |
| `results/medium_by_suffix/000.txt` 至 `999.txt` | 全部末三位子集；选择与本人学号末三位相同的文件即可 |
| `results/medium_validation.json` | 全量覆盖/格式检查，以及独立重算 1,000 个用户的 Top-10：0 处不一致 |

本次完成 6 个真实 Hadoop 3.3.6 + Java 11 作业，使用 **LocalJobRunner + 本机文件系统**，非 4 VM / YARN 或 IE DIC。原始作业日志与 counters 在 `results/hadoop_medium_verified/`。这些结果可核对算法与答案，但不能充当课程要求的云集群运行证据；按课程要求重跑时可直接使用同一套代码与已记录的数据校验值。

本包没有签署原创声明，也没有把推测耗时写成测量结果。原题要求学生独立完成自己的提交并明确注明来源；这些材料供理解、实现核查与实验复现使用，不能原封不动声称为独立创作。需要按课程允许的方式披露 AI 辅助，署名与声明由本人据实填写。

## 2. 先在本地核对算法

以下命令从本包根目录运行，仅需 Python 3.10+：

```bash
python3 -m unittest discover -s tests -v
python3 src/local_demo.py data/figure_numeric.txt --output results/figure_top10.txt
```

本地测试包括 100 个固定种子的随机图与独立集合交集算法逐项对照。此外，已在真实 Hadoop 3.3.6 + Java 11 的 LocalJobRunner 下跑通题图与回归图，核对复合键、分区、二级排序、重复边及超过 64 位的 ID。该执行环境使用本机文件系统，不能作为 4 VM / YARN 的实测证据。

题图使用 `A=1, B=2, C=3, D=4, E=5` 后，完整结果为：

```text
1:2 3 5 4
2:1 3 4 5
3:1 2 4 5
4:2 1 3 5
5:1 2 3 4
```

## 3. 数据语义必须核对

题面写的是微博数据，规模约 1000 / 250 万 / 480 万用户；附件里的下载文件名却为 `facebook_combined` / `twitter_combined` / `gplus_combined`。Stanford 同名公开数据的节点数分别为 4,039 / 81,306 / 107,614，不能据文件名就认定其与课程数据相同。

已成功读取原题 Dropbox [7]：实际为 2,420,766 行边、去重后 1,768,149 条边、81,306 个不同用户，和题面“约 250 万用户”不一致。数据还存在重复边，程序会先去重。下载校验值与检查记录在 `results/data_access_status.json`。本包以这个真实课程链接为准，**没有用其他同名下载替代它**。SNAP 官方数据说明将 Twitter/Gplus 的 `a b` 定义为 a 关注 b，本包据此使用第一列 follower。若教师另发不同来源的数据，应重新核对。Yelp 数据需从题目链接按其条款取得。

程序支持两种格式：

| 输入 | 含义 | 参数 |
|---|---|---|
| `8:1 2 3` | 1、2、3 都关注 8 | `adjacency` |
| `1 8` | 默认 1 关注 8 | `edges follower-followee` |
| `8 1` | 若数据文档明确为关注对象在前 | `edges followee-follower` |

`auto` 只判断有没有冒号，**不能判断边方向**。原始 SNAP 说明见 https://snap.stanford.edu/data/readme-Ego.txt 。只有数据明确为无向图时才设置 `UNDIRECTED=1`。ID 必须为非负十进制整数；程序会归一化前导零。

## 4. 在集群上执行

1. 按 `cluster/LAB_E2E.md` 完成单节点验证与 1 master + 3 workers 部署。
2. 将真实课程数据放入 HDFS，按后述命令运行 Q1。
3. 对中数据集运行 Q2，同一程序可用于大数据集 bonus。
4. 对完整结果按学号末 3 位筛选，再补充真实截图与报告表格。

### Q1(b)：Shakespeare 小文件与合并文件

已按原题 [11] 下载并准备好 `data/shakespeare_prepared`：196 个文本小文件，合并后 6,460,189 字节，包含逐文件 SHA-256 manifest。可直接上传：

```bash
hdfs dfs -mkdir -p /hw1/input/shakespeare
hdfs dfs -put data/shakespeare_prepared/small /hw1/input/shakespeare/small
hdfs dfs -put data/shakespeare_prepared/merged.txt /hw1/input/shakespeare/merged.txt
python3 src/run_wordcount.py --mode files \
  --small-input /hw1/input/shakespeare/small \
  --merged-input /hw1/input/shakespeare/merged.txt \
  --output-root /hw1/output/shakespeare_trial1 \
  --evidence results/shakespeare_trial1 --repetitions 3
```

脚本会保留每个 job 的控制台日志、原始 JobHistory JSON、实际 task 数与 `timings.csv`，并对词频结果排序后算 SHA-256，验证两种输入得到相同答案。最后一项验证耗时不计入 Hadoop job 耗时。

本包已用真实 Hadoop 本地模式核对两种输入：196 个 mapper 对 1 个 mapper，均得到相同的 72,379 个不同 token 及词频。参考词频输出在 `results/shakespeare_expected_wordcounts.txt`，校验记录在 `results/shakespeare_validation.json`。这次只验证正确性，不能填入 4 VM 的性能对照表。

### Q1(c)：至少 4 组实际 mapper/reducer

取得 Yelp 数据后，本方案直接将一份**解压后的** Yelp review JSONL 当作文本，不抽样、不重复扩增。报告中必须记录实际文件名、字节数和 SHA-256。若教师要求只统计评论正文，应统一提取 `text` 字段，并在所有设置中使用同一派生文件。

```bash
hdfs dfs -mkdir -p /hw1/input/yelp
hdfs dfs -put data/yelp_academic_dataset_review.json /hw1/input/yelp/reviews.json
python3 src/run_wordcount.py --mode sweep \
  --large-input /hw1/input/yelp/reviews.json \
  --plan 6:1,6:3,12:1,12:3 --repetitions 3 \
  --output-root /hw1/output/yelp_trial1 --evidence results/yelp_trial1
```

不能通过 `mapreduce.job.maps` 直接强制实际 mapper 数。本程序改变输入 split 大小，再从历史记录读出实际 task 数；若最终不足 4 个不同的实际组合，会明确报错。reducers 的数量也以实测为准。

`timings.csv` 的字段 `map_max_s/min_s/avg_s`、`reduce_max_s/min_s/avg_s`、`job_s` 正是题目要求的 7 项。`client_wall_s` 额外记录客户端提交到返回的总时长；两者不可混用。reduce task 时间包含 shuffle、merge/sort、reduce 的全过程。

### Q2：每个用户的 Top-10

可直接从原题链接下载并解压中数据。这样上传到 HDFS 的输入可以分片并行。输出根路径必须不存在：

```bash
python3 src/fetch_course_data.py medium --decompress
hdfs dfs -mkdir -p /hw1/input/community
hdfs dfs -put data/course_medium.txt /hw1/input/community/medium.txt
REDUCERS=6 BLOCK_SIZE=512 bash src/run_community.sh \
  /hw1/input/community/medium.txt /hw1/community_medium_trial1 edges follower-followee
```

原题 [7] 的实际文件为边列表，上述命令据此配置；请核实第一列确为 follower。若教师另发冒号格式文件，改为 `adjacency`。bonus 使用相同程序，将输入路径和输出根目录换成 large。

```bash
hdfs dfs -cat '/hw1/community_medium_trial1/06_top10/part-*' \
  | python3 src/filter_suffix.py --suffix 321 > results/medium_suffix_321.txt
```

将 `321` 换成自己的学号末 3 位，例如 `007`。不需要提供完整学号。程序先对所有用户计算再筛选，不会提前过滤图、导致遗漏相似用户。HDFS 的多份 part 文件共同构成完整输出；行间顺序不影响结果。

### 大图运行前的容量检查

Q2 的六个阶段会分别保存 `01_dedup`、`02_universe`、`03_blocks`、`04_pairs`、`05_scores`、`06_top10`。`04_pairs` 可能非常大，不能根据输入压缩包体积估算所需空间。

```bash
df -h
hdfs dfsadmin -report
hdfs dfs -du -h /hw1
```

`03_blocks` job 的 `HW` counters 包含 `Edges`、`Users`、`CandidatePairs` 与 `ReplicatedFollowerIDs`。其中 `CandidatePairs = sum d_f*(d_f-1)/2` 是配对阶段的精确输出条数预测（未计用户标记）。对已下载的中数据，按第一列为 follower 计算，该值为 **154,933,408**，最大 follower 列表为 3,383。首次大图运行时建议用 `STOP_AFTER_BLOCKS=1` 执行准备阶段，检查 counters 与磁盘；之后用 `RESUME_AFTER_BLOCKS=1` 和相同输入/输出参数继续。不能保证 4 台小规格 VM 在任意大图上均能完成精确两两计算。

分块控制单个配对组的内存和输出规模，但不会消除这个算法的二次工作量。Map 输出压缩节省 shuffle 和 spill 空间，最终 HDFS 中间结果默认仍是未压缩文本。不要把启用了 map 压缩误写成所有中间文件都被压缩。

## 5. 最后还缺的材料

| 必须补齐 | 具体内容 |
|---|---|
| 实验室环境证据 | 四台真实主机的软硬件与网络信息；Thor master、其余三台 workers |
| 安装证据 | 各主机的单节点 smoke test；集群 `jps`、3 个 Live DataNodes、3 个 RUNNING NodeManagers |
| Q1 实测 | 两种 Shakespeare 设置；Yelp 至少 4 个不同实际 M/R 组合；真实表格及分析 |
| Q2 运行证据 | 中数据 all-user Top-10 与全部末三位结果已提供；在本次实验集群重跑并保留证据；大数据为 bonus |
| 本人信息 | 姓名、SID、讨论与来源说明、本人核实后的声明与签名 |

集群仍需取得实验室主机的实际 SSH 接入方式才能部署，本包没有申请收费资源。所有 `NOT MEASURED` 必须在真实实验后替换，旧 PDF 的云环境描述也待真实环境核对后统一更新。
