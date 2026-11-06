# 实验室四台物理机：接续方案

更新于 2026-11-06。按用户决定改用实验室设备，不再申请云资源。本文件是当前部署入口；`DEPLOYMENT.md` 和 `TENCENT_E2E.md` 中的云平台选择是历史方案。

**状态：部署脚本已适配，尚未连接实验室主机；集群运行、截图和性能测量尚未完成。** 原有中图完整结果来自 Hadoop LocalJobRunner，不能作为本次四机运行证据。原报告 PDF 的云环境段落是旧草稿，待真实实验后统一改为本次环境。

## 1. 固定拓扑与访问

| 物理设备 | 本文示例名称 | 角色 | 服务 |
|---|---|---|---|
| 独立 Jetson Thor | thor | master | NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer |
| H800 所在的 NUMA 双节点主机 | h800 | worker1 | DataNode、NodeManager |
| 第一台独立 RTX 5090 主机 | rtx5090a | worker2 | DataNode、NodeManager |
| 第二台独立 RTX 5090 主机 | rtx5090b | worker3 | DataNode、NodeManager |

这是四台物理主机，不需要将 H800 的两个 NUMA 节点虚拟成两台机器。Hadoop WordCount 和本包 Python Streaming 不请求 GPU。优先让三个工作节点采用相同的 CPU 架构；先用 `uname -m` 验证，不能根据显卡型号判断主机 CPU。

需要四台的 SSH 地址、端口、用户名，以及 VPN/跳板机要求。口令和私钥不放进聊天或作业包。只有私网 IP 时，执行环境还必须有实际可用的内网接入路径；拿到地址本身不代表已能连接。保持现有主机密钥验证。

四机的真实可达地址需互相解析。示例名只是占位符，不能直接当作已配置好的 DNS。Hadoop 控制/数据服务仅供实验网络访问，Web 页面通过 SSH 隧道查看。不要修改实验室现有集群的端口、数据目录、CUDA、驱动或默认 Java。

## 2. 每台先采集只读环境信息

将本包放到各自账号下，在每台机器执行一次：

```bash
python3 cluster/lab_preflight.py --work-dir "$HOME" > "preflight-$(hostname -s).json"
bash cluster/bootstrap_node.sh --plan
```

如果实验目录位于另一块盘，`--work-dir` 改成那块盘上**已经存在**的目录。这份检查包含 OS/架构、CPU/NUMA、RAM、可写磁盘空间、网卡本地链路信息、Java/Python、监听端口；不安装软件、不启动服务、不执行 GPU 命令。它不等于网络吞吐或集群性能测试。后续还需核对本账号可用资源、四机互通和共享负载。

建议的起始配置是每个 worker 至少有 4 个可用逻辑 CPU、8 GiB 可用 RAM、100 GiB 可用工作空间；它是规划起点，**不是中/大图的容量保证**。标准档给 YARN 4 vcores / 6144 MiB、单任务 1536 MiB。四种 Yelp 设置固定为 `6:1,6:3,12:1,12:3`。实际资源和重复次数在跑实验前固定并记录。YARN 资源额度主要用于调度；默认配置不保证 CPU 的硬隔离，需避免同机负载变化影响比较。

H800 的 NUMA 绑核在确认 CPU 分布和账号可用核后再决定；无须为了完成本作业改变 GPU 拓扑。

## 3. 按架构安装，在每个节点本地生成配置

统一 Hadoop 3.3.6 + JDK 11。保留 Thor 原有系统/JetPack；无需把四机刷成相同 Ubuntu 版本。Apache 提供同版本的 x86_64 和 aarch64 二进制包：

| 检测到的架构 | 下载包 |
|---|---|
| x86_64 / amd64 | hadoop-3.3.6.tar.gz |
| aarch64 / arm64 | hadoop-3.3.6-aarch64.tar.gz |

`bootstrap_node.sh` 默认只安装到用户 HOME，验证 Apache SHA-512，并选择本机 JDK 11。缺少依赖时会退出说明原因。需要使用已有或用户目录中的 JDK 时，先设置本机 `JAVA_HOME`。不要直接复制 x86_64 JDK 到 Thor。`--install-deps` 是需要 sudo 的可选 apt 安装路径；不能假设 Thor 的系统仓库一定提供 JDK 11。

```bash
bash cluster/bootstrap_node.sh
source "$HOME/hadoop-env-user.sh"
```

如果用户目录已有同名 Hadoop 安装，脚本会复用它；须检查它的版本及本地库架构。`hadoop checknative -a` 可辅助检查；不使用的可选 codec 缺失要区别于实际所用功能失败。不要在不同架构之间复制整个 Hadoop 安装目录。

先按 `DEPLOYMENT.md` 第 2 节，使用每台的真实主机名和独立 `hadoop-single` 目录，分别完成单节点 smoke test，并保留截图、停止本次单节点服务。若用户名、安装路径不同，使用下文逐节点启动方式，避免脚本假定远程路径相同。

接着在**每台机器本地**运行下面的生成命令（替换示例主机名），这样即使 SSH 用户名和 HOME 不同，本地数据路径也正确：

```bash
source "$HOME/hadoop-env-user.sh"
python3 cluster/configure.py --mode multi --profile standard \
  --master thor --workers h800 rtx5090a rtx5090b \
  --data-root "$HOME/hw1-lab/multi" --output generated-lab
cp generated-lab/*.xml generated-lab/workers "$HADOOP_HOME/etc/hadoop/"
cat generated-lab/homework-env.sh >> "$HADOOP_HOME/etc/hadoop/hadoop-env.sh"
source generated-lab/homework-env.sh
```

这组命令只在初次安装配置时追加一次。`homework-env.sh` 从每台各自的 `hadoop-env-user.sh` 读取 JDK/安装路径，不将 ARM64 master 的 Java 路径写死到 x86 workers。所有实验目录必须由本次账号拥有，并与已有集群分开；如已发现 Hadoop 服务或端口冲突，先选用完整独立配置，不能停止其他人的服务。既有云指南中跨节点复制环境文件和 `start-*.sh` 的步骤以本文件为准。

只在 **Thor 上、确认本次 NameNode 目录为空**后执行一次 format；已有数据时禁止重复：

```bash
hdfs namenode -format -nonInteractive
hdfs --daemon start namenode
hdfs --daemon start secondarynamenode
yarn --daemon start resourcemanager
```

在 **H800、5090a、5090b 各自的登录 shell**中，加载该机环境后执行：

```bash
source "$HOME/hadoop-env-user.sh"
hdfs --daemon start datanode
yarn --daemon start nodemanager
```

回到 Thor：

```bash
hdfs dfs -mkdir -p "/user/$(id -un)" /hw1 /mr-history/tmp /mr-history/done
mapred --daemon start historyserver
hdfs dfsadmin -report
yarn node -list
```

必须看到 **3 个 Live DataNodes + 3 个 RUNNING NodeManagers**。Thor 不运行 DataNode/NodeManager。逐节点启动避免了账号/HOME 不同的 SSH 脚本假设；本次临时实验使用可互信的实验账号，若四机用户名不同，还需按实际账号设置本次 HDFS/YARN 目录权限，不要对整个实验室目录执行全局 chmod。

## 4. 数据、必做实验与证据

原 ZIP 交付包含中图和 Shakespeare 输入；**本 Git 版本不包含原始数据**。先按 `../README.md` 下载并准备，核对 manifest，再上传中图：

```bash
# 若下载时已经 --decompress，直接复用并核对，不要再次覆盖。
gzip -dc data/course_medium.txt.gz > data/course_medium.txt
hdfs dfs -mkdir -p /hw1/input/community /hw1/input/yelp
hdfs dfs -put data/course_medium.txt /hw1/input/community/medium.txt
```

Yelp 原文件不在代码包里，当前工作目录也未保留该 5 GB 原文件，需要在实验节点重新从官方地址取得；不要把原来的“已下载”记录误认为当前文件仍可用。历史输入记录位于 `results/yelp_input_manifest.json`：

- 官方资源页：<https://business.yelp.com/data/resources/open-dataset/>
- 公开 ZIP：<https://business.yelp.com/external-assets/files/Yelp-JSON.zip>
- 原先完整 review JSONL 为 5,341,868,833 字节，SHA-256 为 `a4edc050d14eec25373a75e7ee211d42f49f14f47230837d8c7849eb9c5f2f96`。

ZIP 内的 `Yelp JSON/yelp_dataset.tar` 实际采用 gzip 压缩，提取时按文件内容识别，不能按扩展名认定是未压缩 tar。若官方更新了数据，重新记录实际大小和哈希，并保证所有配置使用同一份未压缩 review JSONL。上传 Yelp 后，先跑一次完整必做链路验证；正式对照可将 `REPETITIONS=3`：

```bash
hdfs dfs -put data/yelp_academic_dataset_review.json /hw1/input/yelp/reviews.json
source generated-lab/homework-env.sh
REPETITIONS=1 bash cluster/run_required.sh \
  /hw1/input/yelp/reviews.json /hw1/input/community/medium.txt
```

总入口兼容 standard / lowmem，执行 Shakespeare 两种设置、Yelp 四组设置和 Q2 中数据六阶段，使用新输出路径，不删除原数据。保留原始 JobHistory、实际 M/R 数、task max/min/mean、总 job 时间和结果校验。运行过程中查看磁盘，尤其是中图 154,933,408 条配对贡献对应的阶段；bonus 仍须单独做容量检查。

截图使用实际节点信息、进程、HDFS/YARN 和 History 页面；报告写为“实验室四台物理主机”，记录软硬件、网卡、共用负载、资源上限、重复次数及计时方法。不要写成云 VM、GPU 加速或已经完成测量。待实测完成后再更新旧 PDF 的环境表与 NOT MEASURED 字段。

参考：Apache [3.3.6 官方归档](https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/)、[集群部署文档](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/ClusterSetup.html)、[本地库说明](https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/NativeLibraries.html)。
