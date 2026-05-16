# Block 4: ModuleTree 交互 — 点击切换模块

**粒度：** 中 (2-3min)

## 文件
- `web/components/learning/ModuleTree.tsx` — 加 onClick + 高亮
- `web/app/(workspace)/learning/[bookId]/page.tsx` — 处理点击切换

## 代码要求
按 `.hermes_plan.md` Block 4 实现：
1. ModuleTree: 每个模块节点加 `onClick(moduleId)` —— 样式区分当前模块（高亮背景）
2. [bookId]/page.tsx: 点击模块 → `setCurrentModuleId(id)` + WebSocket 发 `{type: "change_module", module_id: id}`
3. 当前模块重新点击 → 不触发

## 验收命令
```bash
grep -n "onClick\|currentModuleId\|change_module\|onModuleSelect" web/components/learning/ModuleTree.tsx web/app/\(workspace\)/learning/\[bookId\]/page.tsx
```
