# 四台物理机的实际实验

本次 run ID：`lab-20261106T110350Z`，2026-11-06。

## 当前已验证

1. Thor 为独立 aarch64 master；H800 主机与两台 5090 各为一个 x86_64 worker。使用既有 SSH 别名、本账号和用户目录 runtime；未更改系统 Java、驱动、账号、网络或他人服务。
2. 四台分别通过真实 HDFS/YARN 单节点 WordCount。随后切换独立 multi 命名空间，首次 format 后显示 3 Live DataNode、3 RUNNING NodeManager；跨节点 smoke 实际在三个 workers 执行。
3. Shakespeare 两种布局各三次，196/1 个实际 mapper、均 1 reducer；六次词频完全一致。小文件中位数 76.364 s，merged 8.430 s，实测中位数速度比 9.06。
4. 中图六个 YARN jobs 成功，输出全部 81,306 用户；覆盖/格式检查、1,000 独立抽样和完整参考排名比较均零误差。先检查 stage03 的 154,933,408 CandidatePairs 与磁盘，再展开配对。
5. 完整 Yelp review JSONL 为 5,341,868,833 bytes，源文件 SHA-256 与交接记录一致。已完成四组 6:1、6:3、12:1、12:3，各 3 次真实作业；输出完全一致。四组中位数依次为 135.032、174.556、121.511、117.878 s。

## 结果位置

- 公开证据：[evidence/lab-20261106T110350Z](../homework1/evidence/lab-20261106T110350Z/)。包含环境/输入/runtime manifest、每次 History JSON、实际任务、计数器、CSV、真实服务页面截图与验证。
- 全量新答案：[medium_all_users_top10_lab-20261106T110350Z.txt.gz](../homework1/artifacts/medium_all_users_top10_lab-20261106T110350Z.txt.gz)。按用户逐一比较候选顺序，不能用旧 raw SHA 代替语义核验。
- 全部后缀：[medium_by_suffix_lab-20261106T110350Z.tar.gz](../homework1/artifacts/medium_by_suffix_lab-20261106T110350Z.tar.gz)。`000.txt` 至 `999.txt`，合计 81,306 行；完整计算后才过滤，不需要披露完整 SID。
- 原始私密记录：当前 checkout 的 `.local/` 与 `homework1/results/lab-20261106T110350Z/`，默认不提交。真实地址/账号仅在本地 inventory 与 JVM hosts 文件。

## 固定配置与测量边界

每 worker：6144 MiB / 4 YARN vcores，map/reduce 1536 MiB / heap 768 MiB，AM 1536 MiB / heap 1024 MiB。H800 worker 的进程 CPU affinity 为 80–83，两台 5090 workers 为 16–19。GPU 不参与计算，H800 两个 NUMA 节点没有拆成两台机器。HDFS replication=3、blocksize=128 MiB；关闭推测执行，shuffle 使用 DefaultCodec。

配置、NameNode/checkpoint、PID 和日志位于本次独立目录；所有固定服务端口偏移 20000。每个 JVM/容器读取实验专用 hosts 文件，未改系统 DNS。Thor 不运行 worker 服务。原有服务的端口和目录未覆盖。

JobHistory 的 job/task `finishTime-startTime` 为测量来源。每种任务报告 max/min/mean，reduce 包括 shuffle、sort、reduce；并行 task 时间不能相加当作 job 时间。CSV 还保存实际 M/R、job ID、失败尝试和输出哈希。

机器共享；Shakespeare 比较期间 H800 在后台下载 Yelp，没有并行提交其他 Hadoop jobs。Q2 正确性运行期间存在 Yelp 准备 I/O，因此 Q2 阶段时间只描述本次执行，不当作受控性能对比。Yelp 实测在完整下载、解包、上传与 Q2 验证结束后开始。

## 本机复核

```bash
cd ~/cisc8003
python3 scripts/verify_repository.py
python3 -m unittest discover -s homework1/tests -v
source .local/conf/multi/homework-env.sh
hdfs dfsadmin -report
yarn node -list
```

不要重新运行 format。现有结果保持原路径；新实验必须使用新 HDFS 输出根和本地证据目录。正式配置/控制通过 `homework1/cluster/lab_node.sh` 与实验专用配置目录完成，不能停止别人的服务。

原课程部署环境要求与用户选择的实验室方案不同，报告如实披露；没有声称取得教师正式认可。大图 bonus 已在2026-11-07单独完成，见下节；中图测量保持原值。姓名、完整 SID、声明和签名由学生本人核实填写。

## 2026-11-07 独立大图 bonus

Run `bonus-20261107T061207Z`。原题Gplus gzip398,930,514bytes，解压1,341,774,104bytes，直接来源/重定向/方向和完整SHA在本轮input-manifest/source-redirects。实测30,494,866输入行、13,673,453唯一有向边、107,614用户；不使用题面近似用户数。

候选配对10,984,048,711；原始文本三副本不足，容量检查后04/05用DefaultCodec单副本、后半64reducers、block512不变。原输入/01–03/最终06仍三副本。仅bonus配置将三个worker各调整到8vcores/12GiB，H800的shuffle使用另一已有文件系统，单task内存/heap保持1536/768MiB；07:23UTC在stage05期间，实测H800约231GiB可用内存/96CPU后，以原生rmadmin在线增至24vcores/36GiB，affinity72–95；其他两台仍8vcores/12GiB，不重启NM/容器，资源变化详见online-resource-update。原Q1/中图资源和性能表不变。H800 NM初次本地启动未驻留的问题已按工作日志修复，没有失败job attempt由此产生。

| Stage | Actual job ID | Maps/reducers | Seconds |
|---|---|---|---|
| 01_dedup | job_1793963521105_0026 | 10/6 | 53.216 |
| 02_universe | job_1793963521105_0027 | 6/1 | 8.161 |
| 03_blocks | job_1793963521105_0028 | 6/6 | 26.131 |
| 04_pairs | job_1793963521105_0035 | 6/64 | 509.392 |
| 05_scores | job_1793963521105_0036 | 64/64 | 4764.398 |
| 06_top10 | job_1793963521105_0037 | 64/64 | 602.970 |

全用户覆盖、格式和候选合法性通过，固定seed20261107的1,000用户加定向样本共1064用户独立精确排名零差异。没有声称独立重算全部用户排名。SQLite源索引峰值711.711MiB；验证峰值509.457MiB。 全部1,000suffix流式导出并逐行/集合/字节哈希核验，总107,614行。全量结果SHA-256 `8fa379b42403b5ffe9f4d0541d9d1ab955d4418d0c2e800bb7c1d494a2b1587d`。

公开证据 `homework1/evidence/lab-bonus-20261107T061207Z/`；完整结果及suffix在artifacts中，压缩与每个tar成员哈希已核对。真实未脱敏记录仍在本轮results与.local。最终PDF与兼容Draft.pdf字节相同；旧24页PDF可从b6670cc6 Git历史和本地baseline-report追溯。交付位置和本人待办见README及FINAL_SUBMISSION。
