# doc/ 目录结构说明

本文档目录用于集中管理 OminiConfig 项目的所有技术文档。

## 目录结构

```
doc/
├── README.md                    # 本文档：目录结构总览
├── architecture/               # 架构设计文档
│   ├── README.md              # 架构文档索引
│   ├── v1_overview.md         # v1 版本架构概览
│   └── v2_enterprise.md       # v2 企业级架构设计
├── guides/                     # 开发指南
│   ├── README.md              # 指南索引
│   ├── getting_started.md     # 快速开始指南
│   └── development_workflow.md # 开发工作流程
├── api/                        # API 文档
│   ├── README.md              # API 文档索引
│   ├── rest_api.md            # REST API 参考
│   └── sse_specification.md   # SSE 实时接口规范
└── standards/                  # 规范与标准
    ├── README.md              # 规范索引
    ├── coding_standards.md    # 代码规范
    ├── testing_standards.md   # 测试规范
    └── commit_convention.md   # 提交规范
```

## 文档命名规范

1. **使用小写字母和下划线**：`file_name.md`
2. **使用语义化名称**：反映文档内容
3. **版本号处理**：对于版本化文档，使用 `v{n}_{description}.md`
4. **保持简洁**：文件名不超过 30 个字符

## 文档模板

每个文档文件应包含以下头部信息：

```markdown
# 文档标题

**文档类型**: [架构设计 | 开发指南 | API 文档 | 规范标准]
**适用范围**: [v1.0+ | v2.0+ | 全版本]
**最后更新**: YYYY-MM-DD
**维护者**: [作者名]

## 文档用途
[简要说明本文档的目的和读者群体]

## 内容概述
[文档的主要内容大纲]

---

[正文内容...]
```

## 维护责任

- **架构文档**: 由架构师维护，重大变更需评审
- **API 文档**: 由后端开发人员维护，随代码同步更新
- **开发指南**: 由技术负责人维护，定期更新最佳实践
- **规范标准**: 由团队共同维护，变更需全员共识

## 文档更新流程

1. 在对应目录下创建或修改文档
2. 更新本文档（doc/README.md）的目录索引
3. 如果涉及规范变更，同步更新 AGENTS.md
4. 提交时包含文档变更说明
