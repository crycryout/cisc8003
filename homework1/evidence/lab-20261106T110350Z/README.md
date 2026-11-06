# 本次真实四机证据

Run：`lab-20261106T110350Z`，2026-11-06。一个 aarch64 Thor master、三个 x86_64 物理 workers；HDFS/YARN 为 Hadoop 3.3.6。历史 LocalJobRunner 结果不在本次性能表中。

| 目录 / 文件 | 核对内容 |
|---|---|
| [environment.json](environment.json)、[runtime-manifest.json](runtime-manifest.json)、[experiment-conditions.json](experiment-conditions.json) | 实际硬件/OS、官方校验值、固定资源、输入/重复顺序与共享负载 |
| [single-node](single-node/) / [cluster](cluster/) | 四个单节点成功作业、3 DN / 3 NM、跨节点 smoke、进程与容器 CPU affinity、逐节点真实配置 |
| [shakespeare/timings.csv](shakespeare/timings.csv)、[shakespeare/comparison.json](shakespeare/comparison.json) | 六个真实 jobs、七项时间、实际 M/R、相同词频；中位数 76.364/8.430 s |
| [yelp/timings.csv](yelp/timings.csv)、[yelp-input-manifest.json](yelp-input-manifest.json) | 完整官方 review JSONL 的实际参数对照；四组各三次共 12 个成功 jobs 合并于同一 CSV，保留每次 job/task/counter/attempt JSON |
| [community](community/) / [screenshots](screenshots/) | 中图六阶段、实际容量 gate、81,306 用户完整检查、1,000 抽样、全量参考比较、全部 suffix 计数和真实服务页面截图 |

各运行目录内的 `job.json`、`tasks.json`、`counters.json`、`attempts.json` 来自真正完成的 JobHistory REST。`summary.json` 与 CSV 为据此计算的值；`command.json` 保存实际命令数组。主机地址/名称和账号字段已脱敏，job ID、时间戳、状态、计数器、候选排名和哈希保留。未经脱敏的原始文件留在当前机器忽略的 `.local/` 与 `results/lab-*/`。

截图来自真正的 Hadoop 服务页面；只有访问地址/账号标签替换为角色名，图中附有 privacy 标识，没有画图冒充运行结果。配置目录的 `original-checksums.json` 对应未脱敏原文件 SHA-256，公开配置只改主机和账号标签。

新结果归档：

- [全量 81,306 用户 Top-10](../../artifacts/medium_all_users_top10_lab-20261106T110350Z.txt.gz)。[完整参考比较](community/reference_comparison.json)忽略用户行序、逐一比较候选顺序，零差异。
- [全部 000–999 后缀](../../artifacts/medium_by_suffix_lab-20261106T110350Z.tar.gz)。在所有用户计算完成后导出，归档不含本机账号的 tar 元数据。
- [文件大小和 SHA-256](result-artifacts.json)。原始课程输入和 Yelp 不进入 Git。

`unit-tests.log` 是 18 项本地回归验证，覆盖算法、计时统计、隔离配置与断流续传；它不作为性能表或四机部署证据。
