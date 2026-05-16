# Block 2: 后端 list_all + import 端点 + 摘要

**粒度：** 中 (2-3min)

## 文件
- `deeptutor/learning/storage.py` — 加 `list_all()` 方法
- `deeptutor/learning/service.py` — 加 `list_progress()` 摘要方法
- `deeptutor/api/routers/guided_learning.py` — 加 GET /progress 端点（无 {book_id} 参数，列所有 book 摘要）

## 代码要求

1. **storage.py** 加 `list_all() -> list[str]`: 扫描 `data/learning/progress/` 目录，返回所有 `.json` 文件名（去后缀），排除 `.` 开头的文件
2. **service.py** 加 `list_progress() -> list[dict]`: 调 `store.list_all()`，对每个 book_id 读 progress，返回摘要 `[{book_id, modules_count, kp_count, current_stage, mastered_pct, updated_at}, ...]`
3. **router 第68行之前** 加 `GET /progress` 端点（必须在 GET /progress/{book_id} 之前，避免路由 shadowing）：
   - 调 `service.list_progress()`，返回列表

## 验收命令
```bash
cd D:/Project/DeepTutor && python -c "
from deeptutor.learning.storage import LearningStore
s = LearningStore()
ids = s.list_all()
print(f'list_all: {ids}')
assert 'default' in ids, 'default book missing'
print('Block 2 OK')
"
```
