# Block 3: 前端 API 客户端 + learning 页面重设计

**粒度：** 大 (5-10min)

## 概述
- 扩展 `web/lib/learning-api.ts`：加 fetchAllProgress、importFromBook、deleteProgress、redoProgress
- 重写 `web/app/(workspace)/learning/page.tsx`：多 book tab 面板 + 进度卡片 + 删除/重做

## 文件
- `web/lib/learning-api.ts` — 加 4 个 API 函数
- `web/app/(workspace)/learning/page.tsx` — 重写
- `web/locales/en/app.json`、`web/locales/zh/app.json` — 补删除/重做/空状态 i18n

## 代码要求
详见 `.hermes_plan.md` Block 3 的完整代码片段（learning-api.ts 函数签名 + page.tsx 卡片/删除/重做按钮代码 + i18n keys）

## 验收命令
```bash
grep -n "fetchAllProgress\|importFromBook\|deleteProgress\|redoProgress" web/lib/learning-api.ts && grep -n "tab\|Tab\|当前学习\|已完成\|全部\|fetchAllProgress" web/app/\(workspace\)/learning/page.tsx
```
