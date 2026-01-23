# 后端测试模块

这个目录包含后端API的单元测试和集成测试。

## 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_api.py -v

# 查看测试覆盖率
pytest tests/ --cov=backend --cov-report=html
```

## 测试文件说明

- `test_api.py`: API接口测试
- `test_database.py`: 数据库操作测试（待添加）
- `test_models.py`: 数据模型测试（待添加）

## 注意事项

- 所有测试文件必须以 `test_` 开头
- 测试函数必须以 `test_` 开头
- 使用 pytest fixture 管理测试数据
