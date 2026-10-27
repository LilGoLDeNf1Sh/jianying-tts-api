# 剪映 11.5 在线验证记录

日期：2026-10-27

- 本地发现文件与桥接健康检查通过。
- `getToneCategories` 返回 20 个分类。
- 分类分页与 effectId/resourceId 去重后得到 828 个音色，保存在 `voices.json`（不包含账号凭据）。
- 修复 speakerId/resourceId 查询：先从完整目录按 ID 精确匹配，再使用名称搜索。
- 使用普通音色“解说小帅”，speakerId `BV411_streaming` 合成短文本“你好，这是剪映配音接口测试。”。
- `POST /tts` 返回 HTTP 200、Content-Type `audio/mpeg`、60,000 字节，音频 ID `beb94ce37b5d4829bcb8a4f9daa9e286`。
- `output/test.mp3` 已通过 ffmpeg 完整解码检查，无解码错误。

注意：在线测试证明上述账号、客户端及一个音色的调用成功，不代表逐个验证了全部 828 个音色；每个音色仍受账号权限、平台策略与服务端状态约束。
