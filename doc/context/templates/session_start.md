# 会话开始检查清单

## 1. 读取上下文
- [ ] 阅读 doc/context/current.md 了解项目当前状态
- [ ] 查看最近的 git log（git log --oneline -10）
- [ ] 检查项目结构是否有变化（git status）

## 2. 环境检查
- [ ] 确认 Python 版本（python --version）
- [ ] 检查依赖是否最新（pip list | grep -E 'fastapi|pydantic|anyio'）
- [ ] 运行测试确保基准状态（python -m pytest tests/ -v）
- [ ] 启动服务验证功能正常（python main.py）

## 3. 理解当前任务
- [ ] 明确本次会话的目标
- [ ] 查看 "下次会话建议" 部分
- [ ] 识别依赖和前置条件
- [ ] 评估工作量和风险

## 4. 开发准备
- [ ] 拉取最新代码（git pull origin main）
- [ ] 创建功能分支（如需要：git checkout -b feature/xxx）
- [ ] 更新 TODO 列表
- [ ] 准备参考资料

---

**会话开始时间**: ____年__月__日 __:__  
**目标**: [简要描述本次会话要完成的任务]  
**预计时长**: X 小时  
**涉及模块**: [如: core/security.py, api/router.py]

### 环境信息记录
```bash
# 记录当前环境信息
Python版本: 
FastAPI版本: 
Pydantic版本: 
Git分支: 
最新提交: 
```

### 已知问题记录
- 问题 1: [如有]
- 问题 2: [如有]

### 参考资料
- [链接或文档]
- [链接或文档]
