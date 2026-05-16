# Block 1: 侧边栏 /learning 入口 + i18n

**粒度：** 小 (30-60s)

## 文件
- `web/components/sidebar/SidebarShell.tsx` — imports + PRIMARY_NAV 数组
- `web/locales/en/app.json` — 2 个 i18n key
- `web/locales/zh/app.json` — 2 个 i18n key

## 代码要求

1. **SidebarShell.tsx 第9行** imports 加 `GraduationCap` from `lucide-react`
2. **SidebarShell.tsx PRIMARY_NAV 数组**（/knowledge 后、/space 前）插入：
   ```
   { href: "/learning", label: "Learning", icon: GraduationCap, tooltipKey: "Learning tooltip" }
   ```
3. **en/app.json** 加: `"Learning": "Learning"`, `"Learning tooltip": "Structured mastery-based guided learning."`
4. **zh/app.json** 加: `"Learning": "学习"`, `"Learning tooltip": "结构化掌握式引导学习。"`

## 验收命令
```bash
grep -n "GraduationCap" web/components/sidebar/SidebarShell.tsx && grep -n "Learning tooltip" web/locales/en/app.json web/locales/zh/app.json
```
