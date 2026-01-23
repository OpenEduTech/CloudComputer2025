# 测试套件说明
## 测试组织结构
1. test_data_processor.py - DataProcessor 模块单元测试
2. test_question_generator.py - QuestionGenerator 模块单元测试  
3. test_answer_evaluator.py - AnswerEvaluator 模块单元测试
4. test_agent.py - Agent 模块单元测试
5. test_cli_integration.py - CLI 端到端集成测试

### 模块级测试（单元测试）

#### 1. `test_data_processor.py` - 数据处理模块
**测试内容：**
- 文本处理和分块
- 分块的内容和元数据验证
- 文件处理
- 边界情况处理

**核心测试：**
- `test_process_text_returns_chunks` - 文本处理返回分块
- `test_chunks_contain_text` - 分块包含文本内容
- `test_chunks_contain_metadata` - 分块包含元数据

#### 2. `test_question_generator.py` - 题目生成模块
**测试内容：**
- 题目生成器初始化
- 难度分布
- 关键概念提取
- 流式生成和回调机制

**核心测试：**
- `test_select_difficulty_distribution` - 难度分布正确
- `test_extract_key_concepts` - 关键概念提取
- `test_stream_callbacks_are_called` - 流式回调被正确调用

#### 3. `test_answer_evaluator.py` - 答案评估模块
**测试内容：**
- 评估器初始化
- 正确答案评估
- 错误答案评估
- 评估结果完整性

**核心测试：**
- `test_evaluate_correct_answer` - 正确答案评估
- `test_evaluate_wrong_answer` - 错误答案评估
- `test_score_range` - 分数范围验证

#### 4. `test_agent.py` - Agent 协调模块
**测试内容：**
- Agent 初始化
- 资料处理
- 题目生成
- 答案评估
- 题目缓存
- 会话管理

**核心测试：**
- `test_process_material` - 处理学习资料
- `test_generate_questions` - 生成题目
- `test_evaluate_answer` - 评估答案
- `test_question_caching` - 题目缓存

### 集成级测试

#### 5. `test_cli_integration.py` - CLI 端到端集成测试
**测试内容：**
- 完整用户流程（一镜到底）
- 流式生成在 CLI 中的应用
- 多个题目的完整流程
- 性能保存

**核心测试场景：**

**场景1：正确答案流程**
```
输入学习资料 → 生成题目 → 用户正确回答 → 获得满分评估
```

**场景2：错误答案流程**
```
生成题目 → 用户错误回答 → 获得错误反馈和改进建议
```

**场景3：流式生成**
```
实时显示题目生成进度 → 每个数据块触发回调 → 题目完成通知
```

**场景4：多题目流程**
```
生成3个题目 → 依次回答 → 获得分别评估结果
```

## 运行方式

### 运行所有测试
```bash
pytest
# 或详细输出
pytest -v
```

### 运行特定模块的测试
```bash
# 数据处理模块
pytest test/test_data_processor.py -v

# 题目生成模块
pytest test/test_question_generator.py -v

# 答案评估模块
pytest test/test_answer_evaluator.py -v

# Agent 模块
pytest test/test_agent.py -v

# CLI 集成测试
pytest test/test_cli_integration.py -v
```

### 运行特定测试类
```bash
# 运行 CLI 端到端测试类
pytest test/test_cli_integration.py::TestCLIEndToEnd -v

# 运行 CLI 用户交互测试类
pytest test/test_cli_integration.py::TestCLIUserInteraction -v
```

### 运行特定测试
```bash
# 运行完整流程测试（正确答案）
pytest test/test_cli_integration.py::TestCLIEndToEnd::test_complete_user_flow_correct_answer -v

# 运行完整流程测试（错误答案）
pytest test/test_cli_integration.py::TestCLIEndToEnd::test_complete_user_flow_wrong_answer -v

# 运行多题目流程测试
pytest test/test_cli_integration.py::TestCLIEndToEnd::test_multiple_questions_flow -v
```

### 运行带详细报告的测试
```bash
# 显示打印输出
pytest -v -s

# 显示最后 N 行失败信息
pytest -v --tb=short

# 生成 HTML 报告
pytest --html=report.html --self-contained-html
```