# 剪映机器人配音接口（本地）

把剪映客户端的“文本朗读”封装为本地 FastAPI 服务：动态同步音色，输入文本返回 MP3。

## 当前验证状态（重要）

- **离线接口与合成流程：13 项自动化测试覆盖。**
- **剪映 11.5 在线验证通过（2026-10-27）**：成功同步 20 个分类、828 个去重音色；使用“解说小帅”（speakerId `BV411_streaming`）合成“你好，这是剪映配音接口测试。”，接口返回 200 和 60,000 字节 MP3。依赖已登录且正常运行的兼容客户端，并非免客户端云端 TTS。
- 不修改剪映程序，不导出 Cookie，不绕过会员/付费权限；合成由已登录客户端签名并提交。

## 启动

前置条件：Windows、Python 3.11+、能正常启动且已登录的兼容剪映客户端。先打开剪映，再启动本服务。

```powershell
cd "F:\Jianying_Pro\6.0.1.11779 - 副本\jianying-tts-api"
.\setup.ps1
.\start.ps1
```

依赖安装在项目 `.packages` 内，不改全局环境。服务只监听 `127.0.0.1:8000`，接口文档为 <http://127.0.0.1:8000/docs>。

## 接口

### 健康检查

```powershell
curl.exe http://127.0.0.1:8000/health
```

`bridge_ready=false` 表示没有检测到客户端后台发现文件，应先在正常桌面环境打开剪映。

### 同步全部音色

```powershell
curl.exe "http://127.0.0.1:8000/voices?refresh=true"
```

自动读取音色分类、分页、按 effectId/resourceId 去重。结果缓存 5 分钟；`refresh=true` 强制刷新。支持名称、speakerId、resourceId；`isVip` 只是音色会员标记，实际仍由服务端及账号权限决定。

搜索音色：

```powershell
curl.exe "http://127.0.0.1:8000/voices?query=解说小帅"
```

### 合成 MP3

```powershell
curl.exe -X POST http://127.0.0.1:8000/tts `
  -H "Content-Type: application/json" `
  -d '{"text":"你好，这是一段测试","voice":"解说小帅"}' `
  --output test.mp3
```

成功时直接返回 `audio/mpeg`，同时写入 `output/{随机ID}.mp3`。`X-Audio-Id` 返回随机文件 ID，`X-Voice-Name` 是 URL 编码后的音色名。然后可通过 `GET /audio/{X-Audio-Id}` 下载。

```powershell
curl.exe http://127.0.0.1:8000/audio/替换为随机ID --output test.mp3
```

限制：文本 1–120 字；最长等待 90 秒；MP3 最大 25 MiB。超时任务可能仍在客户端处理，请先检查任务状态，不要立即重复提交。

## 错误码

- `403`：当前账号不能使用该会员音色。
- `404`：音色或音频不存在；同名音色需改用 ID。
- `422`：文本为空、超长或请求格式错误。
- `502`：上游任务失败、响应异常或音频下载失败。
- `503`：剪映未运行、后台桥接未就绪或连接超时。

## 测试

```powershell
.\test.ps1
```

测试不访问剪映、不消耗合成配额。在线测试需要先成功启动客户端，然后访问 `/voices?refresh=true`，再从返回的可用音色中选择一个调用 `/tts`。

## 文件结构

- `app/bridge.py`：只读本地发现信息、会话及客户端签名请求。
- `app/catalog.py`：动态音色同步、名称/ID 解析与会员检查。
- `app/synthesizer.py`：SystemTTS 任务、轮询、MP3 验证与保存。
- `app/main.py`：FastAPI 路由及错误映射。
- `tests/`：不消耗配额的离线测试。
- `docs/plans/`：设计说明。
- `THIRD_PARTY_NOTICES.md`：参考项目及许可证说明。

服务令牌仅在使用时读入内存，不写日志、不返回接口。合成文本也不会被本项目主动记录。客户端版本升级后协议可能变化，需要重新验证。
