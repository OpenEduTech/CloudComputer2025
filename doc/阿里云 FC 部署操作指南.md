# 🚀 阿里云 FC 部署操作指南
---

## ✅ 准备工作（成员 A）
1.  **安装 Serverless Devs CLI**
    参考官方文档：https://www.serverless-devs.com
2.  **云服务开通与权限配置**
    在阿里云控制台开通 **Function Compute** 与 **OSS**，并创建 `AccessKey/Role` 或使用 RAM 角色。
3.  **配置文件检查**
    在 `!s.yaml` 中确认 `region`、`cronExpression`、`handler` 路径是否正确。

---

## 🛠️ 部署命令（在项目根目录，PowerShell）
```powershell
# 登录 Serverless Devs（按照指引配置阿里云凭据）
s config add

# 部署函数（会上传代码并创建触发器）
s deploy
```

---

## 🧪 测试触发（部署后）
### 方式 1：本地/远程调用
```powershell
# 使用 s invoke 本地/远程调用（如果已安装并支持）
s invoke -e '{}'   # 或根据 s 文档调用远程函数
```
### 方式 2：阿里云控制台触发
在阿里云控制台里触发一次定时器的执行，查看日志。

---

## ⚙️ 必要的环境变量（成员 A 在控制台或 `!s.yaml` 中设置）
- `SILICONFLOW_API_KEY`（LLM API Key）
- OSS 相关凭据（若 `storage_layer.py` 使用 OSS SDK）
- 其它监控/告警插件配置

---

## 📦 存储层注意事项（成员 A）
- 目前 `storage_layer.py` 使用本地文件。上线时请将其替换为 OSS 客户端实现（读取最新快照并写回新的 JSON），并保证函数有访问 OSS 的权限与合适的超时时间。
- 本地临时目录不可作为持久化存储。

---

## 🔍 成员 B（你）需要确认
- `incremental_analysis.py`、`conflict_resolution.py` 不使用本地硬编码路径（现在已改为接受传入数据）。
- `trigger_layer.py` 已按 FC 要求返回可被监控系统捕获的 JSON（已更新）。

---

## 🎯 可继续推进的任务
如果你愿意，我可以继续：
1.  把 `storage_layer.py` 改为 OSS 示例实现（需要 OSS 凭据与占位配置）。
2.  生成一个更完整的 `!s.yaml`（包含环境变量、Layer 配置与 OSS 权限示例）。
3.  写一份给成员 A 的逐步部署说明文档（含最小权限策略示例）。

---

要不要我帮你生成**带详细注释的 OSS 版 storage_layer.py 代码**？这样你就能直接替换当前的本地文件版本。