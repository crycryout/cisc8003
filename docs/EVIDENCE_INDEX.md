# 证据索引

本仓库历史运行属于 **2026-11-03 Hadoop 3.3.6 + Java 11 / LocalJobRunner / local file://**，不能作为后续四机 YARN 的截图或性能表。

## 真实本地记录

| 路径（相对 homework1） | 内容 |
|---|---|
| `artifacts/local_hadoop_logs_2026-11-03.tar.gz` | 28 份原始日志，包括中图六阶段、图例、额外回归、lowmem 和 WordCount |
| `artifacts/medium_all_users_top10.txt.gz` | 全部 81,306 用户的精确 Top-10，完整参考结果 |
| `artifacts/shakespeare_expected_wordcounts.txt.gz` | 72,379 个 token 的参考词频 |
| `results/hadoop_job_status.json`、`hadoop_counters_summary.json` | 中图六个 local job IDs、成功状态、真实 counters |
| `results/medium_validation.json`、`hadoop_validation.json` | 全用户覆盖与格式检查、1000 个独立抽样零误差等 |

其他摘要：`data_access_status.json`、`shakespeare_validation.json`、`lowmem_validation.json`、`runtime_versions.txt`、`lab_preparation.json`。历史 `local_tests.log` 是当时测试日志；本次仓库准备的 15 项测试另存 `repository_unit_tests_2026-11-06.log`。

压缩文件的大小/哈希记于 `homework1/artifacts/manifest.json`。全仓库导入内容清单见 `docs/IMPORT_MANIFEST.json`，`scripts/verify_repository.py` 检查其 SHA-256。该 manifest 现已透明刷新为本次完整仓库字节；`base_import_commit` 指向初始导入版本，旧快照保留在 Git 历史。后续有意修改后应重算对应条目，不能为了通过检查隐藏改动。

## 查阅旧结果

在 `homework1` 目录：

```bash
gzip -dc artifacts/medium_all_users_top10.txt.gz > results/medium_all_users_top10.txt
python3 src/export_suffixes.py --input results/medium_all_users_top10.txt \
  --output results/medium_by_suffix
tar -tzf artifacts/local_hadoop_logs_2026-11-03.tar.gz
```

tar 内路径以 `results/` 开头。解压到独立的本地目录查阅，避免覆盖新日志；不要把历史 job_local 标识改成 YARN job ID。

## 核心校验值

| 对象 | SHA-256 |
|---|---|
| 原始中图 gzip（10,621,918 bytes） | `d9f99b0e6a53b9204b8c215f41b3c10fb99a1e1e783858c012b06d0d3d4bd129` |
| 旧全量中图输出（7,239,582 bytes） | `1d86de53417447e7a124c0cb9983b2761c834125e9e4620802c9d65a1b655ed9` |
| 规范 Shakespeare 参考词频 | `b9524c8e2c10b2b16d2e5334f34dc3384cb7c46b47f2a770c023d54cae877d31` |
| 原先 Yelp review JSONL（5,341,868,833 bytes） | `a4edc050d14eec25373a75e7ee211d42f49f14f47230837d8c7849eb9c5f2f96` |

新集群输出行序可能因 reducers/partition 不同而变化，旧中图 raw SHA 只用于确认旧文件字节。使用 `scripts/compare_top10.py` 按 user 比较完整排名，另用 `validate_medium.py` 从原始图独立抽样验证。

## 后续四机证据约定

每轮以真实 UTC run ID 建独立目录（例如 `homework1/results/lab-20261107T...`），先本地保存原始输出。这些目录默认 gitignore，避免把 IP、巨量中间结果或未检查截图公开；将可公开的环境摘要、计时 CSV、校验、job/counter 索引和最终报告放入明确的跟踪目录后提交。

至少记录：四个物理节点与角色、资源/配置、输入大小和哈希、单节点/集群成功截图、3 DN/3 NM、Q1 各实际 M/R 和七项时间、Q2 六 job IDs、全量结果/1000 抽样/完整参考比对、suffix 与未完成项。初始导入时尚无这些证据；本次真实四机证据见下节。

## 2026-11-06 真实四台物理机 HDFS/YARN

本次公开证据根为 `homework1/evidence/lab-20261106T110350Z/`。`single-node/` 保存四台独立单节点的成功 job、任务、输出和日志；`cluster/` 保存 3 DN / 3 NM、跨节点 smoke、native 库与进程 CPU affinity；`shakespeare/` 保存六个成功作业的原始 History、counters、attempts、CSV 与相同词频哈希；`community/` 保存六阶段 jobs、容量检查、独立 1000 抽样、81306 用户完整参考比对和 suffix manifest。`yelp/` 保存四种实际 M/R 各三轮的 12 个成功作业、完整七项时间和一致输出；最终集群汇总为 25 个四机 YARN 作业全部成功。

本次全量答案 `artifacts/medium_all_users_top10_lab-20261106T110350Z.txt.gz` 和全部 1000 个后缀 `artifacts/medium_by_suffix_lab-20261106T110350Z.tar.gz` 为真实四机新结果，不能与初始本地归档混称。大小/哈希在 `result-artifacts.json`；tar 不含本机账号 UID/用户名元数据。

公开 JSON、终端日志和真实页面截图只替换/遮蔽私网地址、主机访问名称和账号标识，保留 job ID、时间、计数器、状态和结果。未经脱敏的原始记录、完整配置/命令和 preflight 仍在忽略的 `.local/` 与本次 `results/lab-*/`，不提交私钥、登录配置、原始 Yelp 或庞大中间文件。
