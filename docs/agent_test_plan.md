# AI Diary 多Agent架构测试方案

## 前置条件

⚠️ **重要**：测试前请先配置GitHub CLI认证

```bash
# 检查认证状态
gh auth status

# 如果未认证，执行登录
gh auth login
# 选择：GitHub.com → HTTPS → Paste an authentication token
# 粘贴你的 GitHub Personal Access Token
```

---

## 测试1：Backend Agent触发测试

### 测试目标
验证backend Agent能被正确触发并执行后端开发任务

### 测试步骤
1. 在对话中输入：`帮我在后端添加一个健康检查API端点 /api/health-check`
2. 观察是否触发backend Agent
3. 检查是否生成了正确的Python代码

### 预期结果
- ✅ 触发backend Agent
- ✅ 生成的代码遵循项目规范
- ✅ 代码包含正确的类型注解
- ✅ 建议编写测试用例

---

## 测试2：iOS Agent触发测试

### 测试目标
验证iOS Agent能被正确触发并执行iOS开发任务

### 测试步骤
1. 在对话中输入：`帮我在iOS端添加一个设置页面`
2. 观察是否触发iOS Agent
3. 检查是否生成了正确的SwiftUI代码

### 预期结果
- ✅ 触发iOS Agent
- ✅ 生成的SwiftUI代码符合MVVM架构
- ✅ 考虑了缓存策略
- ✅ 代码遵循Swift命名规范

---

## 测试3：Test Agent触发测试

### 测试目标
验证test Agent能被正确触发并编写测试用例

### 测试步骤
1. 在对话中输入：`为日记创建API编写单元测试`
2. 观察是否触发test Agent
3. 检查是否生成了pytest测试代码

### 预期结果
- ✅ 触发test Agent
- ✅ 生成pytest测试代码
- ✅ 测试覆盖正常和异常场景
- ✅ 使用了正确的fixture

---

## 测试4：Bug Agent触发测试

### 测试目标
验证bug Agent能被正确触发并发现代码问题

### 测试步骤
1. 在对话中输入：`检查项目代码质量并创建Issue`
2. 观察是否触发bug Agent
3. 检查是否分析了代码
4. 检查是否创建了GitHub Issue

### 预期结果
- ✅ 触发bug Agent
- ✅ 分析了代码质量
- ✅ 发现了潜在问题
- ⚠️ 创建Issue（需要gh auth配置）

---

## 测试5：多Agent协作测试

### 测试目标
验证多个Agent能协同工作

### 测试步骤
1. 在对话中输入：`添加一个日记导出为PDF的功能`
2. 观察是否：
   - backend Agent添加导出API
   - iOS Agent添加导出按钮
   - test Agent编写测试
   - bug Agent检查代码质量

### 预期结果
- ✅ 主控Agent正确分解任务
- ✅ backend Agent处理后端部分
- ✅ iOS Agent处理前端部分
- ✅ test Agent编写测试
- ✅ bug Agent检查质量

---

## 测试6：Skill加载测试

### 测试目标
验证Skills能正确加载并提供指导

### 测试步骤
1. 在对话中输入：`实现记忆系统的时间衰减功能`
2. 观察是否引用了memory-system Skill的内容

### 预期结果
- ✅ 加载memory-system Skill
- ✅ 引用架构设计文档
- ✅ 提供实现指导

---

## 验证清单

### 文件验证
- [ ] 4个Agent配置文件存在
- [ ] 2个Skill配置文件存在
- [ ] 旧Agent配置已删除
- [ ] 项目AGENTS.md已更新

### 功能验证
- [ ] backend Agent能被触发
- [ ] iOS Agent能被触发
- [ ] test Agent能被触发
- [ ] bug Agent能被触发
- [ ] Agent之间能协作

### 配置验证
- [ ] 所有Agent使用统一模型（glm-5）
- [ ] 所有Agent都有正确的权限（write/edit/bash）
- [ ] 所有Agent都是subagent模式

---

## 常见问题

### Q1: Agent没有被触发怎么办？
**A**: 检查description字段是否包含正确的关键词，尝试在对话中明确提及

### Q2: Bug Agent创建Issue失败怎么办？
**A**: 需要先配置GitHub CLI认证：
```bash
gh auth login
```

### Q3: Agent生成的代码不符合规范怎么办？
**A**: 检查Agent配置文件中的"开发规范"部分是否清晰

### Q4: 如何验证Agent真的在工作？
**A**: 查看Agent的输出，应该包含：
- 明确的任务分解
- 遵循项目规范的代码
- 测试建议
- 文档说明

---

## 测试报告模板

### 测试时间
YYYY-MM-DD HH:MM

### 测试人员
[你的名字]

### 测试结果
| 测试项 | 结果 | 备注 |
|--------|------|------|
| Backend Agent触发 | ✅/❌ | |
| iOS Agent触发 | ✅/❌ | |
| Test Agent触发 | ✅/❌ | |
| Bug Agent触发 | ✅/❌ | |
| 多Agent协作 | ✅/❌ | |
| Skill加载 | ✅/❌ | |

### 发现的问题
1. 问题描述
2. 问题原因
3. 解决方案

### 改进建议
1. 建议1
2. 建议2
3. 建议3
