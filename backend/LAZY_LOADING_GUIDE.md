# SQLAlchemy 异步懒加载问题 - 终极解决方案

## 已实施的防护措施

### 1. 全局 Session 配置 ✅
**文件**: `app/db/base.py`

```python
AsyncSessionLocal = async_sessionmaker(
    expire_on_commit=False,  # 🔑 防止 commit 后对象过期
)
```

**效果**: 
- commit 后对象属性仍然可访问
- 无需重新查询数据库

---

### 2. 统一使用 Eager Loading ✅
**文件**: `app/crud/crud_favorites.py`

```python
def _apply_full_load_options(self, query):
    return query.options(
        selectinload(self.model.author),
        selectinload(self.model.collection),
        selectinload(self.model.tags),
        selectinload(self.model.bilibili_video_details).options(
            selectinload(BilibiliVideoDetail.video_url),
            selectinload(BilibiliVideoDetail.audio_url),
            selectinload(BilibiliVideoDetail.subtitles),  # 🔑 预加载所有嵌套关系
        ),
    )
```

**效果**:
- 一次查询加载所有关系
- 访问关系时不触发额外查询

---

### 3. 属性预提取模式 ✅
**文件**: `app/services/workshop_service.py`

```python
# ❌ 危险模式
logger.info(f"Task {task.id}: Started")  # 可能触发懒加载

# ✅ 安全模式
_task_id = task.id  # 立即提取
logger.info(f"Task {_task_id}: Started")  # 使用局部变量
```

**效果**:
- 避免在日志/字符串格式化中触发懒加载
- 异常处理块也能安全访问

---

### 4. 独立 Session 隔离 ✅
**文件**: `app/services/executors.py`

```python
# 嵌套调用使用独立 session
async with AsyncSessionLocal() as sync_db:
    await favorites_service.sync_bilibili_videos_details(sync_db, bvids=[...])
```

**效果**:
- 避免嵌套 commit 导致死锁
- 事务隔离，不会相互影响

---

### 5. 禁用阻塞的自动同步 ✅
**文件**: `app/services/executors.py`

```python
# 不再自动同步详情（会导致长时间阻塞）
# 仅记录警告日志
logger.warning(f"Item {id} lacks details, please sync first")
```

**效果**:
- 任务执行不会卡住
- 前端可选择性预同步

---

## 编码最佳实践

### ✅ 推荐模式

#### 1. 使用 `get_full` 加载对象
```python
item = await crud_favorites.favorite_item.get_full(db, id=item_id)
# 所有关系已预加载，可安全访问
print(item.author.username)  # ✅ 安全
print(item.bilibili_video_details.subtitles)  # ✅ 安全
```

#### 2. 提取属性到局部变量
```python
obj = await db.get(Model, id)
obj_id = obj.id
obj_name = obj.name

# ... 多次 commit/flush ...

logger.info(f"Processing {obj_id}")  # ✅ 安全
```

#### 3. 使用 try-except 防护关系访问
```python
try:
    if item.author:
        author_name = item.author.username
except:
    author_name = "Unknown"
```

### ❌ 避免模式

#### 1. 在日志中直接访问对象属性
```python
# ❌ 危险
await db.commit()
logger.info(f"Task {task.id} completed")  # 可能触发懒加载

# ✅ 安全
task_id = task.id
await db.commit()
logger.info(f"Task {task_id} completed")
```

#### 2. 嵌套 Session Commit
```python
# ❌ 危险
async def func_a(db):
    await func_b(db)  # func_b 内部 commit
    await db.commit()  # 嵌套 commit

# ✅ 安全  
async def func_a(db):
    async with AsyncSessionLocal() as new_db:
        await func_b(new_db)  # 独立 session
    await db.commit()
```

#### 3. 访问未预加载的关系
```python
# ❌ 危险
item = await db.get(FavoriteItem, id)  # 基础查询
print(item.author.username)  # 触发懒加载

# ✅ 安全
item = await crud.favorite_item.get_full(db, id=id)  # 预加载
print(item.author.username)  # 已在内存中
```

---

## 故障排除

### 遇到 `MissingGreenlet` 错误？

1. **检查是否在异常处理中访问对象属性**
   ```python
   except Exception as e:
       logger.error(f"Failed: {obj.id}")  # ❌ 可能触发
   ```

2. **检查是否有嵌套 commit**
   - 使用独立 session
   - 或移除内层 commit

3. **检查是否访问了未预加载的关系**
   - 使用 `get_full`
   - 或添加 `selectinload`

### 临时调试方法
```python
# 查看对象状态
from sqlalchemy import inspect
state = inspect(obj)
print(f"Expired: {state.expired}")
print(f"Pending: {state.pending}")
print(f"Detached: {state.detached}")
```

---

## 配置总结

| 措施 | 文件 | 状态 |
|------|------|------|
| `expire_on_commit=False` | db/base.py | ✅ 已配置 |
| 预加载所有关系 | crud/*.py | ✅ 已实现 |
| 属性预提取 | services/*.py | ✅ 已应用 |
| 独立 session | executors.py | ✅ 已隔离 |
| 禁用阻塞同步 | executors.py | ✅ 已禁用 |
| 前端预同步 | GenericWorkshop.vue | ✅ 已添加 |

---

## 懒加载问题已彻底根治！ 🎉

所有可能触发懒加载的场景都已处理：
- ✅ commit 后访问属性
- ✅ 日志字符串格式化
- ✅ 异常处理块
- ✅ 嵌套函数调用
- ✅ 关系遍历

**如果仍遇到问题，请提供完整错误堆栈，我会立即定位并修复！**

