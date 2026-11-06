# 4 VM Hadoop 部署步骤

目标：Q1(a) 先在每台 VM 验证伪分布式 Hadoop；随后切换为 Q1(b) 的 1 master + 3 workers。下列配置选用 Ubuntu 22.04 x86_64、Java 11、Hadoop 3.3.6，满足题目 Hadoop >= 2.7.1 的要求。题面 Ubuntu 14.04 是推荐项，不是强制版本。

## 1. 准备 VM 与网络

使用题目允许的 AWS、GCP 或 Azure。推荐起点是每台 4 vCPU、8 GiB RAM；master 40 GiB 系统盘、workers 每台至少 100 GiB 工作盘只是小规模测试起点，**不是中/大图容量保证**。先读取配对数量 counters 再确定实际空间。记录真实规格、区域、配置、起止时间。这里不提供未经核实的价格或完成时间。

| 名称 | 服务 |
|---|---|
| master | NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer |
| worker1 | DataNode、NodeManager |
| worker2 | DataNode、NodeManager |
| worker3 | DataNode、NodeManager |

4 台放在同一私有网络与区域。安全组允许四台私网互通；SSH 22 仅对自己的 IP 开放。无认证的 Hadoop Web/RPC 服务不要暴露到公网，Web 界面通过 SSH tunnel 查看。

在**每台** VM 的 `/etc/hosts` 中添加真实私网 IP，例如（必须替换示例地址）：

```text
10.0.1.10 master
10.0.1.11 worker1
10.0.1.12 worker2
10.0.1.13 worker3
```

确认 hostname 解析到可达的私网 IP，而不是回环地址。用同一个非 root 用户（以下以 `ubuntu` 为例）操作。把本包传到每台 VM 的 `~/homework1_worked_package`。

```bash
bash ~/homework1_worked_package/cluster/bootstrap_node.sh
source ~/hadoop-env-user.sh
```

在每台配置该用户到本机的免密 SSH；在 master 配置到三台 worker 的免密 SSH。使用现有的云登录方式安装公钥，不要把私钥放进作业包：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ''
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
ssh localhost true
```

若该密钥已存在，保留现有密钥，不要覆盖。master 需要通过既有登录通道把它的公钥追加到每个 worker 的 `authorized_keys`，然后逐个执行 `ssh worker1 true`、`ssh worker2 true`、`ssh worker3 true` 验证。首次连接应核对主机指纹，不关闭主机密钥验证。

## 2. 每台分别执行单节点验证

以下命令**每台各执行一次**；`hostname -s` 必须已映射到该 VM 的私网地址。每台只让自己作为 worker：

```bash
source ~/hadoop-env-user.sh
cd ~/homework1_worked_package
python3 cluster/configure.py --mode single --master "$(hostname -s)" \
  --data-root "$HOME/hadoop-single" --output generated-single
cp generated-single/*.xml generated-single/workers "$HADOOP_HOME/etc/hadoop/"
cat generated-single/homework-env.sh >> "$HADOOP_HOME/etc/hadoop/hadoop-env.sh"
```

下面的 format 只可用于**本次新建且尚未存有数据**的单节点目录；已有 NameNode 数据时不能重做：

```bash
hdfs namenode -format -nonInteractive
start-dfs.sh
start-yarn.sh
hdfs dfs -mkdir -p "/user/$(id -un)" /mr-history/tmp /mr-history/done
mapred --daemon start historyserver
printf 'hello hadoop\nhello mapreduce\n' > /tmp/hw1-smoke.txt
hdfs dfs -put /tmp/hw1-smoke.txt /smoke-input
hadoop jar "$HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-3.3.6.jar" \
  wordcount /smoke-input /smoke-output
hdfs dfs -cat '/smoke-output/part-*'
jps
```

正确词频为 `hadoop 1`、`hello 2`、`mapreduce 1`。截图需包含节点标识、Hadoop/Java 版本、运行命令、job 成功与实际结果。保留截图后停止每台的单节点服务：

```bash
mapred --daemon stop historyserver
stop-yarn.sh
stop-dfs.sh
```

## 3. 切换为全分布式

**只在 master 生成**共同配置，新的数据根目录与单节点分离：

```bash
source ~/hadoop-env-user.sh
cd ~/homework1_worked_package
python3 cluster/configure.py --mode multi --master master \
  --workers worker1 worker2 worker3 \
  --data-root "$HOME/hadoop-multi" --output generated-multi
cp generated-multi/*.xml generated-multi/workers "$HADOOP_HOME/etc/hadoop/"
cat generated-multi/homework-env.sh >> "$HADOOP_HOME/etc/hadoop/hadoop-env.sh"
```

把 4 个 XML、workers 与环境配置分发给 workers（假定各节点用户名、HOME、Hadoop 安装路径一致）：

```bash
for node in worker1 worker2 worker3; do
  scp generated-multi/*.xml generated-multi/workers "$node:$HADOOP_HOME/etc/hadoop/"
  scp generated-multi/homework-env.sh "$node:/tmp/hw1-env.sh"
  ssh "$node" 'cat /tmp/hw1-env.sh >> "$HOME/hadoop-3.3.6/etc/hadoop/hadoop-env.sh"'
done
```

若使用单独工作盘，把 `--data-root` 改成该盘上的实际绝对路径并赋予运行用户写权限；4 台采用相同挂载路径。不要把大图临时 spill 放在过小的系统盘上。

**只在 master** 对本次新的 multi 目录 format 一次：

```bash
hdfs namenode -format -nonInteractive
start-dfs.sh
start-yarn.sh
hdfs dfs -mkdir -p "/user/$(id -un)" /hw1 /mr-history/tmp /mr-history/done
mapred --daemon start historyserver
hdfs dfsadmin -report
yarn node -list
jps
for node in worker1 worker2 worker3; do ssh "$node" jps; done
```

必须看到 **3 个 Live DataNodes、3 个 RUNNING NodeManagers**。在 master 不启动 DataNode/NodeManager，以保持题目要求的 1+3 结构。再执行一次上节 smoke test，使用新的 `/smoke-input` 与 `/smoke-output` 路径；此时它们属于新 HDFS，不是此前的单节点命名空间。

## 4. 截图与实验

本机开启到 master 的 SSH tunnel（把 `YOUR_MASTER_SSH_HOST` 替换成既有云 SSH 主机）：

```bash
ssh -N -L 9870:localhost:9870 -L 8088:localhost:8088 \
  -L 19888:localhost:19888 ubuntu@YOUR_MASTER_SSH_HOST
```

浏览器访问 `http://localhost:9870`（HDFS）、`http://localhost:8088`（YARN）、`http://localhost:19888`（JobHistory）。浏览器点击链接可能指向私网 hostname；优先从隧道端点进入对应 JobHistory 页面，或按需要增加隧道。

回到本包 `README.md` 运行 Q1/Q2。每个关键步骤保留真实截图：云 VM 清单、单节点、3 个 workers、WordCount 输入与输出、各组 job 的 History、Q2 成功 job 和筛选输出。截图配简短说明，不用生成的示意图冒充集群截图。

## 5. 结束实验

先把 `results/`、完整 Q2 结果和截图复制到持久位置，再停止服务与云资源。关 VM 不一定停止磁盘计费；是否删除云盘由本人按保存需求决定。已有集群不要重新 format，也不要自动删除输入或中间结果。

```bash
mapred --daemon stop historyserver
stop-yarn.sh
stop-dfs.sh
```
