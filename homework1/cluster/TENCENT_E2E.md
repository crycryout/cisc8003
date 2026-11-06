# 腾讯云省钱版：端到端实验接续

> 历史方案，2026-11-06 已按用户决定改用实验室四台物理机；当前入口是 `LAB_E2E.md`。下文“已下载”的 Yelp 大文件不在当前代码包/工作目录中，实验前须重新取得并核对。

当前目标：4 台南京同可用区、同 VPC 的 CVM，2 vCPU / 4 GiB，普通 Ubuntu 22.04 x86_64。Master 系统盘 40 GiB，3 台 Worker 各 100 GiB 通用型 SSD。以按量计费执行必做部分，Yelp 四种 M/R 组合各运行一次；bonus 另行决定。

本次已经准备好低内存配置和一键实验入口。尚未登录云账号、创建 VM，也尚未产生腾讯云的实测结果。现有 Q2 全量结果来自之前的 Hadoop LocalJobRunner，不是云集群证据。

## 执行分工

用户负责：云账号身份验证、充值/付款，以及需要本人接受的协议。实验部署、排错、调度、原始数据保存、性能表和报告可由助手执行。授权云访问时应使用受限、临时的方式，不在聊天里粘贴账号密码、验证码或长期 SecretKey。

## 1. 完成节点访问

创建节点后需要实际的 4 台公网/私网 IP、SSH 用户名、已有的 SSH 访问途径与有效的主机密钥。不要关闭 SSH 主机密钥验证。节点间通过私网互通；Hadoop Web 界面仍通过 SSH tunnel 访问。

Yelp 官方数据已完整下载并提取评论文件：`yelp_academic_dataset_review.json`，大小 5,341,868,833 字节；输入校验值保存在 `results/yelp_input_manifest.json`。原始大文件作为实验输入单独保管，没有放进代码压缩包。云节点接通后可上传到 Master，或从记录的官方公开地址下载并提取同一输入；目前没有云端运行结果。

## 2. 配置 4 GiB 节点

沿用 `DEPLOYMENT.md` 的单节点验证和全分布式流程，两处运行 `configure.py` 时都追加 `--profile lowmem`。例如 Master 的多节点配置：

```bash
python3 cluster/configure.py --profile lowmem --mode multi --master master \
  --workers worker1 worker2 worker3 \
  --data-root "$HOME/hadoop-multi" --output generated-multi-lowmem
```

低内存档参数：

| 参数 | 数值 |
|---|---:|
| 每个 Worker 的 YARN 容器内存总量 | 2048 MiB |
| 每个 Worker 的 YARN vcores | 2 |
| 单个 map/reduce 容器 | 1024 MiB |
| map/reduce Java heap | 512 MiB |
| MapReduce ApplicationMaster 容器 / heap | 512 / 256 MiB |
| Hadoop 守护进程/客户端默认 heap 上限 | 256 MiB |

必须将生成的 XML、workers 和 `homework-env.sh` 的内容按部署指南安装到各节点，再重启相关服务使配置生效。登录 shell 中也需执行 `source generated-multi-lowmem/homework-env.sh`，以便实验脚本得到 `HW1_MEMORY_PROFILE=lowmem`。

不要直接在只有 4 GiB 内存的机器上使用之前的 6 GiB YARN 配置。此档参数仍须在真实 CVM 上验证，不能仅凭配置生成成功声称集群运行成功。

## 3. 运行必做实验

所有数据传输均在计时作业之前完成；不要同时运行互相竞争的实验。

```bash
bash cluster/run_required.sh /hw1/input/yelp/reviews.json /hw1/input/community/medium.txt
```

脚本会执行 Shakespeare 的两种设置、Yelp 的四种 M/R 组合，以及 Q2 中数据的六个阶段；每次生成新的输出目录并保留日志。它不会创建/删除云资源，也不会删除已有 HDFS 数据。

## 4. 完成证据与清理

取得 3 个 Live DataNodes、3 个 RUNNING NodeManagers 的真实截图；保存各 job 的 History 页面、原始 JSON、任务耗时与结果校验。截图应避开身份证、付款、密钥等页面中的敏感信息。将成功实验写回报告，并将实际环境记为腾讯云。

导出成果后再释放本次创建的云资源。任何未实际运行的项目继续保留“未测量”状态。
