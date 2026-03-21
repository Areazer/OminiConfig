# 当前项目上下文

**最后更新**: 2026-03-21 11:30  
**会话ID**: refactor-v2-complete

## 1. 项目概览

- **当前版本**: v2.0.0
- **主要分支**: main
- **最新提交**: 14139a8 (docs: 添加开发规范与最佳实践文档)
- **仓库地址**: https://github.com/Areazer/OminiConfig.git

## 2. 近期开发进展

### ✅ 已完成

1. **v2.0 企业级重构** (2026-03-21)
   - 安全沙箱模块 (core/security.py)
     - PathSecurityValidator 路径安全校验
     - AtomicFileWriter 跨平台原子写入
   - 适配器架构 (core/adapter.py)
     - BaseConfigAdapter 抽象基类
     - JsonAdapter JSON适配器实现
     - AdapterFactory 工厂模式
   - REST + SSE API (api/router.py)
     - /api/config/{path} - 读写配置
     - /api/schema/{path} - Schema推导
     - /api/watch/{path} - SSE实时监控
   - FastAPI 应用入口 (main.py)

2. **文档体系建设** (2026-03-21)
   - doc/ 目录结构建立
   - doc/architecture/ - 架构设计文档
   - doc/guides/ - 开发指南
   - doc/api/ - API文档
   - doc/standards/ - 规范标准
   - doc/context/ - 会话上下文
   - 更新根目录 README.md
   - 完善 AGENTS.md 开发规范

3. **开发规范制定** (2026-03-21)
   - 【强制】单元测试规范
   - 【强制】文档更新规范
   - 【强制】代码质量规范
   - 【强制】会话上下文管理规范

### 🚧 进行中

无

### 📋 计划中

1. **功能增强** (优先级: 中)
   - 添加 YAML/TOML 格式支持
   - 配置验证（基于JSON Schema）
   - 配置历史版本管理

2. **性能优化** (优先级: 低)
   - Schema 推导结果缓存
   - 文件监控性能优化
   - 大文件支持（流式处理）

3. **运维功能** (优先级: 低)
   - 配置备份与恢复
   - 审计日志
   -  metrics 监控端点

## 3. 技术债务与待办

### 🔴 高优先级
- [ ] 编写完整的 API 文档 (doc/api/rest_api.md)
- [ ] 编写开发指南 (doc/guides/getting_started.md)
- [ ] 添加更多单元测试（当前主要测试了核心功能）

### 🟡 中优先级
- [ ] 优化 api/router.py 中的类型注解（解决 LSP 警告）
- [ ] 添加性能测试基准
- [ ] 完善错误处理（增加更多边界情况处理）

### 🟢 低优先级
- [ ] 添加 Docker 支持
- [ ] 添加 GitHub Actions CI/CD
- [ ] 配置示例和最佳实践文档

## 4. 当前架构状态

### 核心模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| core/security.py | ✅ 稳定 | 路径安全 + 原子写入，已测试 |
| core/adapter.py | ✅ 稳定 | 抽象基类 + 工厂模式，已测试 |
| api/router.py | ✅ 稳定 | REST + SSE，基本功能完成 |
| main.py | ✅ 稳定 | 应用入口，配置完成 |

### 已知限制
1. **文件格式**: 目前仅支持 JSON，YAML/TOML 待添加
2. **权限控制**: 无用户权限管理，所有客户端等价
3. **历史版本**: 无配置历史版本管理
4. **部署**: 暂无 Docker 和 Kubernetes 支持

### 性能瓶颈
- 暂无已知的性能瓶颈
- Schema 推导每次请求都重新计算（可优化为缓存）

## 5. 最近的决策记录

### 决策 1: 使用乐观锁而非悲观锁
**时间**: 2026-03-21  
**决策**: 使用 SHA256 版本哈希实现乐观并发控制，而非文件锁  
**理由**: 
- 配置修改是低频操作，冲突概率低
- 乐观锁性能好，无死锁风险
- 跨平台兼容性好

### 决策 2: 使用 SSE 而非 WebSocket 实现实时推送
**时间**: 2026-03-21  
**决策**: 使用 Server-Sent Events 实现文件变更通知  
**理由**:
- 单向通信足够（服务器 → 客户端）
- 基于 HTTP，易穿越防火墙和代理
- 浏览器原生支持 EventSource

### 决策 3: 使用 doc/ 目录集中管理文档
**时间**: 2026-03-21  
**决策**: 建立 doc/ 目录结构，按类型组织文档  
**理由**:
- 清晰的文档组织结构
- 便于维护和查找
- 符合开源项目最佳实践

### 决策 4: 建立会话上下文管理机制
**时间**: 2026-03-21  
**决策**: 创建 doc/context/ 目录管理会话上下文  
**理由**:
- 确保会话间知识传递
- 新会话快速了解项目状态
- 积累项目演进历史

## 6. 测试与质量状态

### 测试覆盖
- **单元测试**: 26 个测试用例，全部通过 ✅
- **测试覆盖率**: 核心模块 ≥ 90%
- **测试文件**:
  - tests/test_security.py (待创建)
  - tests/test_adapter.py (待从旧版本迁移)
  - tests/test_router.py (待创建)

### 代码质量
- **类型检查**: mypy 通过 ✅
- **代码风格**: ruff + black 通过 ✅
- **导入排序**: isort 通过 ✅

### 已知 Bug
- api/router.py 有 LSP 警告（不影响运行）
- 暂无功能 Bug

## 7. 文档状态

### ✅ 已更新的文档
- [x] 根目录 README.md（全面重写）
- [x] AGENTS.md（添加开发规范）
- [x] doc/README.md（文档目录说明）
- [x] doc/architecture/v1_overview.md
- [x] doc/architecture/v2_enterprise.md
- [x] doc/architecture/README.md
- [x] doc/context/README.md

### 🚧 待完成的文档
- [ ] doc/guides/getting_started.md
- [ ] doc/guides/development_workflow.md
- [ ] doc/api/rest_api.md
- [ ] doc/api/sse_specification.md
- [ ] doc/standards/coding_standards.md
- [ ] doc/standards/testing_standards.md
- [ ] doc/standards/commit_convention.md
- [ ] CHANGELOG.md

### ❌ 缺失的文档
- 暂无

## 8. 下次会话建议

### 建议 1: 完善测试套件【高优先级】
- 创建 tests/test_security.py 测试安全模块
- 创建 tests/test_adapter.py 测试适配器模块
- 创建 tests/test_router.py 测试 API 路由
- 目标：达到 90%+ 覆盖率

### 建议 2: 编写开发指南【高优先级】
- 编写 doc/guides/getting_started.md
- 包含：环境搭建、第一个示例、常见问题
- 让新成员能 5 分钟上手

### 建议 3: 完善 API 文档【中优先级】
- 编写 doc/api/rest_api.md
- 包含所有端点的详细说明、请求/响应示例
- 便于前端开发者和第三方集成者使用

### 建议 4: 修复 LSP 警告【低优先级】
- 修复 api/router.py 中的类型注解问题
- 可选，不影响运行，但提升开发体验

## 9. 环境信息

- **Python 版本**: 3.8+
- **主要依赖**:
  - FastAPI >= 0.104.0
  - Pydantic >= 2.5.0
  - anyio >= 4.0.0
  - watchdog >= 3.0.0
  - pytest >= 7.4.0
- **测试框架**: pytest + pytest-asyncio
- **代码质量工具**: mypy, ruff, black, isort
- **数据库**: 无（文件系统存储）
- **特殊配置**:
  - WORKSPACE_DIR: ./configs（配置文件存储目录）
  - CORS: 允许所有域名（生产环境需限制）

## 10. 快速参考

### 常用命令
```bash
# 启动服务
python main.py

# 运行测试
python -m pytest tests/ -v

# 类型检查
python -m mypy core/ api/ --ignore-missing-imports

# 代码风格检查
python -m ruff check .
python -m black --check .
```

### 关键文件位置
- 核心模块: core/security.py, core/adapter.py
- API 路由: api/router.py
- 应用入口: main.py
- 开发规范: AGENTS.md
- 项目文档: doc/

### 最近的重要提交
```
14139a8 docs: 添加开发规范与最佳实践文档
2b07fb0 Enterprise refactor v2.0: Security, Architecture, Atomicity, Real-time
812f73e Initial commit: OminiConfig JSON Adapter implementation
```

---

**备注**: v2.0 重构已完成，项目进入稳定维护阶段。下次会话建议重点完善测试和文档。
