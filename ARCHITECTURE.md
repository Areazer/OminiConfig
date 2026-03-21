# OminiConfig JSON Adapter Implementation

## 1. 架构思考 Chain of Thought

### 文件读写锁与并发控制
- **乐观并发控制 (OCC)**: 使用 `versionHash`（基于 MD5/SHA256）实现乐观锁
- **原子写入**: 使用临时文件+重命名方式，保证写入的原子性，避免写入过程中断导致文件损坏
- **无显式文件锁**: 通过版本校验替代重量级文件锁，更轻量高效

### Schema 推导逻辑
1. 递归遍历配置数据的每个字段
2. 根据值的类型推断 JSON Schema 类型:
   - 字符串 → `{"type": "string"}`
   - 数字 → `{"type": "number"}`
   - 布尔 → `{"type": "boolean"}`
   - 数组 → `{"type": "array", "items": {...}}`
   - 对象 → `{"type": "object", "properties": {...}}`
3. 支持嵌套层级无限扩展，通过递归处理

### 错误处理策略
- 文件不存在 → 自动初始化空配置
- JSON 解析错误 → 抛出 `ConfigFormatException`，保留原始堆栈
- 并发冲突 → 抛出 `ConcurrencyConflictException`，携带期望和实际的 versionHash
- 类型不匹配 → 在 Schema 生成阶段标记为 `any` 类型，确保前端可正常渲染
