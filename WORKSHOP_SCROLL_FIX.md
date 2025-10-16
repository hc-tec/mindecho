# 工坊页面滚动修复

**问题**: 左右两边没有实现独立滚动

---

## 🎯 修改内容

### 1. 外层容器
**修改前**: `<div class="flex-1 grid ... overflow-hidden">`
**修改后**: `<div class="flex-1 grid ...">`（移除 overflow-hidden）

### 2. 左侧列表容器
**修改前**: `<div class="bg-background flex flex-col overflow-hidden">`
**修改后**: `<div class="bg-background flex flex-col h-full max-h-full">`

**目的**:
- `h-full` 确保左侧占满可用高度
- `max-h-full` 防止超出父容器
- 内部的 `overflow-y-auto` 区域可以独立滚动

### 3. 右侧结果容器
**修改前**: `<div class="... overflow-hidden"><div class="flex-1 overflow-y-auto">`
**修改后**: `<div class="..."><div class="flex-1">`

**目的**:
- 移除所有滚动限制
- 内容自然展示（不裁剪）

---

## 📐 布局结构

```
<div class="h-full flex flex-col">              ← 根容器（占满视口）
  <header class="shrink-0">...</header>         ← 固定头部

  <div class="flex-1 grid grid-cols-3">         ← 主内容区（flex-1 占满剩余高度）

    <!-- 左侧：固定高度 + 内部滚动 -->
    <div class="h-full max-h-full flex flex-col">
      <div class="shrink-0">头部</div>          ← 固定
      <div class="flex-1 overflow-y-auto">      ← 滚动区域（独立滚动）
        列表项...
      </div>
      <div class="shrink-0">分页</div>          ← 固定
      <div class="shrink-0">按钮</div>          ← 固定
    </div>

    <!-- 右侧：内容自然展示 -->
    <div class="col-span-2 flex flex-col">
      <div class="shrink-0">标题</div>          ← 固定
      <div class="flex-1">                      ← 内容区域（无滚动限制）
        AI 结果内容...
      </div>
    </div>

  </div>
</div>
```

---

## ✅ 预期效果

### 左侧列表
- ✅ 固定在视口左侧
- ✅ 高度受限（不超出屏幕）
- ✅ 内部可滚动查看所有收藏项
- ✅ 头部、分页、按钮始终可见

### 右侧结果
- ✅ 内容自然展示
- ✅ 不受高度限制
- ✅ AI 结果完整显示（不裁剪）

---

**修改文件**: `frontend/app/components/workshops/GenericWorkshop.vue`
**修改行数**: 3 处关键调整
