# Retail AI Star Report

每月追踪 GitHub 上与多模态大模型、商超巡检、零售视觉和电商理解相关的开源项目，
按两次月度快照之间的 Star 增长量选出 Top 10，并通过 QQ 邮箱发送报告。

## 工作方式

- GitHub Actions 在每月 1 日北京时间 09:00 运行，统计上一个自然月。
- 脚本使用多组主题查询发现候选仓库，合并去重后保存当前 Star 快照。
- 排名使用本次 Star 数减去上次快照 Star 数；首次运行只建立基线。
- 每次运行都会把 `data/` 中的新快照提交回仓库，供下月比较。
- 新发现且上月快照中不存在的仓库不会虚增月增长量，会从下一周期开始参与排名。

## 必需的 GitHub Secrets

在仓库的 **Settings → Secrets and variables → Actions** 中添加：

| Secret | 内容 |
| --- | --- |
| `SMTP_USERNAME` | QQ 邮箱发件地址，例如 `307149416@qq.com` |
| `SMTP_APP_PASSWORD` | QQ 邮箱 SMTP 授权码，不是 QQ 登录密码 |

收件地址默认是 `307149416@qq.com`，可在工作流的 `REPORT_RECIPIENT` 中修改。

需要先在 QQ 邮箱设置中开启 POP3/SMTP 或 IMAP/SMTP 服务并生成授权码。
不要把密码或授权码提交到仓库。

## 手动运行

配置 Secrets 后，在仓库 **Actions → Monthly Retail AI Star Report → Run workflow**
执行一次以建立首份基线。也可以用以下命令本地运行：

```bash
GITHUB_TOKEN=... \
SMTP_USERNAME=... \
SMTP_APP_PASSWORD=... \
python3 report.py
```

如只想生成快照和报告预览而不发邮件：

```bash
GITHUB_TOKEN=... DRY_RUN=1 python3 report.py
```
