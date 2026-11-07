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

## 2026-11-06：H800 实际接续，四机单节点与集群启动

1. 在 H800 拉取仓库；导入的 63 个文件哈希全部通过，原有 15 项测试通过。按已安装的多机器远程开发与服务器管理 skills，用既有 SSH 别名连通独立 Thor 与两台 5090 的本账号。原始地址、UID、端口和 preflight 保存在忽略的 `.local/`。
2. 四台实测架构为一个 aarch64 master 和三个 x86_64 workers。H800 是 96 逻辑 CPU / 251.3 GiB RAM；两个 5090 主机均为 Core Ultra 7 265K、20 逻辑 CPU / 62.2 GiB RAM。Hadoop 3.3.6 两架构包通过 Apache SHA-512，用户目录 Corretto JDK 11.0.33.0.10 两架构包通过厂商 SHA-256。没有改系统默认 Java、GPU 软件、账户组或网络配置。
3. 四台各自独立 HDFS/YARN 单节点的真实 WordCount 均成功，hello/hadoop/mapreduce 的计数为 2/1/1。成功 job IDs、原始 History、终端日志与真实服务页面截图已保存；公开证据目录为 `homework1/evidence/lab-20261106T110350Z/`，截图仅遮蔽访问地址与账号名称。
4. 由于默认 9000 端口被已有服务占用，本次固定所有服务端口偏移 20000，配置、NameNode、checkpoint、PID、日志和工作目录独立。新增每个 JVM/容器使用的 hosts 文件支持，避免修改系统 DNS；新增两项配置回归，17 项测试通过。单节点服务只停止本次命名空间；四机新 namespace 仅首次 format，已实测 3 Live DN / 3 RUNNING NM。
5. 新中图原始 gzip 与交接 SHA-256 一致；Shakespeare 再次准备为 196 文件、6,460,189 bytes 的等价输入。Yelp 官方完整 ZIP 正在按校验 byte range 下载。配置同步首轮用了旧脚本而失败，已重新同步并保留失败日志；正式性能实验尚未开始，不能将当前 smoke 或历史本地作业填入性能表。

四机 smoke 使用六个实际 mapper 与三个 reducer 成功（`job_1793963521105_0001`），聚合输出 hello/hadoop/mapreduce 为 12/6/6，History 任务记录完整。已开始 Shakespeare 每种输入三次、交替顺序的实际比较；本轮期间 H800 后台仍在下载 Yelp，作为共享 I/O 条件记录。

Shakespeare 三轮已完成：小文件 job 时间 75.648/76.364/77.015 秒，merged 8.241/9.459/8.430 秒；实际 maps 为 196/1，reducers 均为 1。中位数速度比 9.0586；六次规范输出 SHA-256 全部为 `b9524c8e2c10b2b16d2e5334f34dc3384cb7c46b47f2a770c023d54cae877d31`，与历史参考词频相同。每次 History job/tasks/counters/attempts 与 CSV 均已保留；任务 attempts 证明小文件作业实际在三个 workers 执行。

中图前三个 YARN jobs 成功，stage03 的实际 HW counters：81,306 users、1,768,149 unique edges、154,933,408 CandidatePairs、2,032,942 ReplicatedFollowerIDs。三个 worker 均有超过 100 GiB 的剩余工作盘，按每候选对 256 bytes 的保守临时预算检查通过，才使用 RESUME_AFTER_BLOCKS 继续 stages04–06；容量估计不作为运行耗时或 bonus 完成证据。

Yelp 官方 ZIP 4,345,335,132 bytes 下载完成；提取完整 review JSONL 5,341,868,833 bytes，SHA-256 为 `a4edc050d14eec25373a75e7ee211d42f49f14f47230837d8c7849eb9c5f2f96`，与交接记录完全一致。新增真实本地 HTTP 断流续传/嵌套 gzip-tar 解包回归测试，18 项测试通过；该测试不提供性能证据。

本次中图六阶段全部成功：job IDs `job_1793963521105_0008` 至 `_0013`；实际阶段 job 时间为 16.669/8.281/13.345/38.374/118.407/112.363 秒，不与历史 LocalJobRunner 混合。新输出 81,306 用户，覆盖/格式/候选合法性通过，1,000 用户独立重算零误差，全量历史参考逐用户排名比对零误差。新字节 SHA-256 `cb6d2f7776b031314f648996bf24392774388eea261befca077172c5aaf4899f`；用户行序不同于旧文件，语义完全一致。已导出 000–999 全部 suffix，合计 81,306 行；全量与 suffix 的本次压缩归档纳入 artifacts。

Yelp 第一完整 sweep 已成功，实际 M/R=6/1、6/3、12/1、12/3，job 时间分别 125.302、174.556、124.663、112.895 秒；job IDs `_0014` 至 `_0017`。四份完整 WordCount 输出的规范 SHA-256 均为 `841320a7bf34efe2546c6efb85d4a87a2556795e28ae6871e017bde7deec6224`，七项 task/job 时间齐全，无失败 attempts。必做实测已完成；资源与输入保持不变，按全局逆序/正序补第 2、3 轮至每组 3 次，使用新的输出根且保留所有原始记录。

## 2026-11-06：最终实测与产物

Yelp 四种实际 M/R 各三次共 12 个 jobs 全部成功，输入/资源没有更换，按正序/逆序/正序执行。Job IDs 为 `job_1793963521105_0014` 至 `_0025`，无失败 map/reduce attempts；完整词频 SHA-256 全部相同。四组中位数：6/1=135.032 s，6/3=174.556 s，12/1=121.511 s，12/3=117.878 s。每个单独值、七项任务统计、原始 History 与任务分布均保留，不只报告最快值。不同 6-map 作业会落到不同的物理主机组合，报告明确指出异构 CPU 与调度位置的影响。

最终 RM 显示本次 25 个四机 YARN apps 全部 SUCCEEDED（smoke 1、Shakespeare 6、中图 6、Yelp 12），NN/RM 仍有 3 live DN / 3 RUNNING NM。18 项测试、Shell 语法和文本差异检查通过。真实报告已更新为四台实验室物理机，包含实际七项时间、真实截图、数据哈希、所有中图验证和 AI 协助/引用；姓名、SID、声明与签名保持待本人填写。大图 bonus 未运行，不作完成声明。

公开证据只遮蔽访问地址与账号标识；真实完整配置、访问元数据和原始日志保存在忽略的本地目录。当前仓库的 IMPORT_MANIFEST 将透明刷新至本次最终内容，初始导入快照保留于 Git 历史和 base_import_commit，不能把更新字节校验当作性能证据。Hadoop 仅保留本次独立服务供复核，未停止或改写他人服务。

实验、真实结果与最终 24 页报告已提交为 `814341d`；373 个文件字节校验无差异，公开文本检查未发现本次私网地址、实际访问主机名或凭据。三台远端均已同步最终任务脚本且 Shell 语法通过；随后单独记录验收状态和最终完整性快照。

## 2026-11-07：大图 bonus 接续任务

用户要求补完剩余项目；需要服务器计算的部分交给服务器 Codex 执行。本轮在会话环境核对了 main 的真实四机证据、runner/metrics 参数、数据下载与恢复接口，新增 docs/BONUS_COMPLETION_HANDOFF.md，并将 NEXT_CODEX_PROMPT.md 更新为当前 bonus 入口。

接续文档覆盖原题 Ref[8] 数据、前三阶段容量检查、六阶段精确全用户运行、阶段 4–6 的恢复限制、流式/磁盘辅助验证与后缀导出、报告与提交包。当前 validate_medium.py 和 export_suffixes.py 的内存使用边界已明确交接；没有把这些准备事项写成已运行大图。

本次会话没有实验室服务器连接配置，未连接服务器、未下载或执行大图、未生成大图答案。Q1/中图实测与原 24 页 PDF 保持既有状态；bonus 仍未完成，待服务器执行并保存证据后更新。姓名/SID/声明/签名与课程政策事项仍须用户本人核实。仓库快照仅透明纳入本轮有意修改的文档，不重写旧实验事实。

## 2026-11-07：服务器实际执行大图，准备阶段检查点

恢复 `main` 后，原 374 文件快照校验无差异、18 项原有测试通过；正常快进至 `6b9f591`，不覆盖未提交工作或旧证据。通过已安装的多机开发 skills 复用原 Thor master 和三个物理 worker，3 live DN / 3 RUNNING NM；Python 单独访问 History REST 成功。未重启 master、未 format，原 Nov6 证据和 24 页 PDF 另有可追溯备份。

原题 Ref[8] Dropbox 链接直接取得 gzip 398,930,514 bytes（SHA-256 `492b7a63ec7816cac6aa0466be8521a0528cb1df2ca7f0b554ad746adc6bbbee`），完整解压 1,341,774,104 bytes（`c3b6e5fa980c688ef783cd6afabc0c17a635e5e7ad8f3edf8396907d3f1ab451`），gzip 完整性检查通过。实际是二列边表，按 Gplus 来源和 SNAP 官方 a follows b 说明显式使用 follower-followee，不做无向扩展，不用题面近似用户数。独立原始输入 SQLite 索引得到 30,494,866 行、13,673,453 唯一有向边、16,821,413 重复边、107,614 endpoint 用户，索引构建峰值 711.711 MiB。

新 run `bonus-20261107T061207Z` 的前三阶段实际成功：`job_1793963521105_0026` / `_0027` / `_0028`，时间 53.216 / 8.161 / 26.131 s。Stage03 counters 与独立索引一致：107,614 Users、13,673,453 Edges、10,984,048,711 CandidatePairs、50,752,824 ReplicatedFollowerIDs。不能将这些准备 jobs 宣称为 bonus 排名完成。

每条配对原始文本 48 bytes，单 stage04 的三副本预计 1,581,703,014,384 bytes，已超过初始 HDFS 剩余 1,459,986,186,240 bytes。按实际候选量和压缩实测作容量预算，阶段04/05将用 DefaultCodec、单副本（丢失时重算），原始输入/01–03/最终06仍三副本；后半段64 reducers，block512保持原 stage03不变。仅本次三个空闲 NM 的独立配置从每台4核6GiB调至8核12GiB，H800 shuffle 使用另一既有文件系统的任务专用目录；没有改系统默认设置、其他账号服务或删除数据。容量假设、spill/合并/倾斜/重试预算见本轮 `capacity-decision.json`，每45秒记录剩余空间与YARN状态；情景估计不作为数学压缩上界或耗时承诺。

新磁盘辅助独立验证器与流式后缀导出不 import community 排名逻辑，任意精度 ID 以字符串/整数处理；新增小图随机与边界测试。28项单元测试通过。对既有中图结果重新独立验证1,000固定种子+定向样本共1,074用户零差异，所有81,306用户覆盖/格式通过，新导出1,000 suffix与原文件逐字节相同。首次回归误传 adjacency 格式而退出，失败记录保留，改用实测二列格式后成功。runner新增明确 `RESUME_FROM_STAGE=1..6`、拒绝已有失败输出/阶段日志和并发锁，以保留失败证据；压缩仅作用于04/05。大图阶段04–06在此检查点尚未执行。

压缩真实 YARN 回归已完成：另建 HDFS 根运行六 jobs `job_1793963521105_0029`–`_0034`，31用户（含21位、超过64位、70/91位边界 ID、空邻接、零分补齐）全部独立精确重算零差异；HDFS确认04/05均为单副本 `.deflate`，最终普通文本可正确读取。此小图只验证实现，不填入 bonus 性能表。已具备继续大图阶段04的条件。

大图阶段04已提交 `job_1793963521105_0035`。监控发现 H800 NM 虽已注册，但本地启动会话结束后进程未驻留，两个远端 worker 仍持续计算、无失败 attempts；改为本账号独立进程会话启动原任务专用 NM 后，三个 worker 各8个容器正常运行。没有重复启动已有活跃 daemon，没有丢弃成功中间结果。追加45秒采样的本任务 Python/JVM RSS、VmHWM与CPU affinity记录；这些是观察到的峰值，不宣称捕获所有瞬时峰值。

阶段04实际成功：`job_1793963521105_0035`，6maps/64reducers，509.392秒；输出10,984,156,325条，等于CandidatePairs+Users，38,095,358,435压缩字节，单副本，比容量情景保守预算小。没有失败map/reduce attempts。阶段05 `job_1793963521105_0036` 已继续运行；监控和持久后处理已配置，后者仅在六阶段计算exit0后采集、独立验证并流式分区。当前仍不可宣称bonus完成。

07:23 UTC阶段05期间，首批23 maps完成后有reducers等待shuffle。H800新预检显示96CPU、load7.72、约231.45GiB可用内存和397.41GB独立shuffle盘空闲，原8核配额留下大量空闲。本账号本次NM通过官方Hadoop3.3.6 `rmadmin -updateNodeResource`在线增至24vcores/36GiB，NM线程affinity72–95；另外两worker保持8核/12GiB，单task1536MiB/heap768MiB不变。RM和NM REST均确认新资源，原NM PID不变、无重启或故意失败task，既有进度保留。按60%最坏情景shuffle/merge分配到H800并加20%倾斜得253.07GB，加3.30GB重试仍低于397.41−95GB预算。原配置hash、更新后hash、实际资源和时间线均保存在online-resource-update；bonus时长包含资源变化，不作为固定配置扩展性对比。Q1/中图表未改动。
