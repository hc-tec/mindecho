# 工作坊配置文件说明

## 概述

MindEcho 使用 JSON 配置文件来定义默认工作坊，避免在代码中硬编码。这使得添加、修改或禁用工作坊变得更加简单和灵活。

## 文件说明

### `workshops.json`
主配置文件，定义了所有默认工作坊的配置。

### `workshops_schema.json`
JSON Schema 文件，用于验证 `workshops.json` 的格式正确性。

## 配置结构

```json
{
  "version": "1.0",
  "description": "配置文件的描述",
  "workshops": [
    {
      "workshop_id": "工作坊唯一ID",
      "name": "工作坊显示名称",
      "description": "工作坊功能描述",
      "default_prompt": "默认提示词模板，使用 {source} 作为内容占位符",
      "default_model": null,
      "executor_type": "llm_chat",
      "enabled": true,
      "tags": ["标签1", "标签2"]
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 是 | 配置文件版本号（格式：x.y） |
| `description` | string | 否 | 配置文件的描述信息 |
| `workshops` | array | 是 | 工作坊配置数组 |

### Workshop 对象字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `workshop_id` | string | 是 | 工作坊唯一标识符（3-50字符，只能包含小写字母、数字和连字符） |
| `name` | string | 是 | 工作坊的显示名称（1-100字符） |
| `description` | string | 否 | 工作坊功能的简要描述 |
| `default_prompt` | string | 是 | 默认提示词模板（至少10字符），必须包含 `{source}` 占位符 |
| `default_model` | string/null | 否 | 默认使用的 AI 模型（null 表示使用系统默认） |
| `executor_type` | string | 是 | 执行器类型（目前只支持 `"llm_chat"`） |
| `enabled` | boolean | 否 | 是否在启动时加载此工作坊（默认：true） |
| `tags` | array | 否 | 工作坊的分类标签 |

## 使用说明

### 添加新工作坊

1. 编辑 `workshops.json` 文件
2. 在 `workshops` 数组中添加新的工作坊对象：

```json
{
  "workshop_id": "my-custom-workshop",
  "name": "我的自定义工作坊",
  "description": "这是一个自定义工作坊的示例",
  "default_prompt": "请按照以下要求处理内容：\n1. ...\n2. ...\n\n{source}",
  "default_model": null,
  "executor_type": "llm_chat",
  "enabled": true,
  "tags": ["自定义", "示例"]
}
```

3. 重启后端服务

### 修改现有工作坊

直接编辑 `workshops.json` 中对应的工作坊配置，然后重启后端服务。

**注意**：修改只影响新创建的工作坊实例。已存在于数据库中的工作坊不会自动更新。

### 禁用工作坊

将工作坊的 `enabled` 字段设置为 `false`：

```json
{
  "workshop_id": "learning-tasks",
  "name": "学习任务",
  "enabled": false,
  ...
}
```

### 提示词模板变量

在 `default_prompt` 中可以使用以下占位符：

- `{source}` - 会被替换为要处理的内容（必需）

示例：
```
请对以下内容进行分析：

{source}

要求：
1. 提取核心观点
2. 总结关键信息
3. 提出相关问题
```

## 验证配置

配置文件会在启动时自动验证。如果配置格式不正确：

1. 后端会在日志中输出错误信息
2. 不会加载该配置的工作坊
3. 回退到硬编码的默认配置（如果配置文件不存在）

可以手动验证配置：

```bash
# 安装 jsonschema 库
pip install jsonschema

# 使用 Python 验证
python -c "
import json
import jsonschema

with open('workshops.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
with open('workshops_schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)

jsonschema.validate(instance=config, schema=schema)
print('✅ 配置文件格式正确')
"
```

## 最佳实践

1. **备份配置**：修改前先备份 `workshops.json`
2. **渐进式修改**：一次只修改一个工作坊，避免批量出错
3. **版本控制**：使用 Git 追踪配置文件的变更
4. **测试验证**：修改后先在开发环境测试
5. **文档注释**：在 `description` 字段中详细说明工作坊用途

## 故障排除

### 配置文件不生效

1. 检查文件路径是否正确：`backend/config/workshops.json`
2. 检查 JSON 格式是否正确（使用 JSON 验证工具）
3. 查看后端启动日志中的错误信息
4. 确认 `enabled` 字段为 `true`

### 验证失败

1. 检查必填字段是否都已填写
2. 检查字段类型是否正确
3. 检查 `workshop_id` 格式（只能包含小写字母、数字和连字符）
4. 检查 `default_prompt` 是否包含 `{source}` 占位符

### 工作坊未出现在界面

1. 确认配置文件已正确加载（查看日志）
2. 检查数据库中是否已有同名工作坊（启动时只会初始化空数据库）
3. 如需重新加载，可以删除数据库文件或清空 `workshops` 表

## 相关文件

- `backend/app/main.py` - 加载配置的代码
- `backend/app/db/models.py` - Workshop 数据模型定义
- `backend/app/api/endpoints/workshops.py` - 工作坊 API 端点

## 示例配置

参考 `workshops.json` 中的默认配置：

- `summary-01` - 精华摘要
- `snapshot-insight` - 快照洞察
- `information-alchemy` - 信息炼金术
- `point-counterpoint` - 观点对撞
- `learning-tasks` - 学习任务

这些工作坊展示了不同的提示词风格和应用场景。
