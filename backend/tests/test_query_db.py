import pytest
import json
from app.services.kg_service import kg_service
from app.db.neo4j_conn import init_neo4j, driver, close_neo4j
import app.db.neo4j_conn  # 导入模块用于monkeypatch


# ==================== 测试前置/后置操作 ====================
@pytest.fixture(scope="module", autouse=True)
def setup_neo4j():
    """测试前初始化Neo4j驱动，测试后关闭"""
    init_neo4j()
    yield
    close_neo4j()


# ==================== 测试用例 ====================
class TestKGQueryDBService:
    """知识图谱查库服务测试类"""

    def test_query_empty_concept(self):
        """测试1：输入空概念 → 抛异常"""
        # 测试空字符串、全空格、None
        with pytest.raises(Exception) as excinfo:
            kg_service.query_db("")
        assert "核心概念不能为空" in str(excinfo.value)

        with pytest.raises(Exception) as excinfo:
            kg_service.query_db("   ")
        assert "核心概念不能为空" in str(excinfo.value)

    def test_query_too_long_concept(self):
        """测试2：输入超过20字的概念 → 抛异常"""
        long_concept = "热力学第二定律熵增原理吉布斯自由能信息熵额热热热热热"  # 21字
        try:
            kg_service.query_db(long_concept)
        except Exception as e:
            # 打印异常信息（能看到完整内容）
            print(f"捕获到异常：{str(e)}")
            # 手动断言
            assert "核心概念长度不能超过20字" in str(e)
            return
        # 如果没抛异常，断言失败
        assert False, "未捕获到预期的长度超限异常"

    def test_query_nonexistent_concept(self):
        """测试3：查询不存在的概念 → 返回has_data=False"""
        nonexistent_concept = "测试概念_123456789"
        result = kg_service.query_db(nonexistent_concept)

        assert result["code"] == 200
        assert result["has_data"] is False
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == nonexistent_concept
        assert len(result["links"]) == 0

    def test_query_existing_concept(self, setup_test_data):
        """测试4：查询存在的概念 → 返回has_data=True"""
        test_concept = "熵"
        result = kg_service.query_db(test_concept)

        assert result["code"] == 200
        assert result["has_data"] is True
        assert len(result["nodes"]) > 1
        assert len(result["links"]) > 0
        for link in result["links"]:
            assert link["strength"] >= 2


# ==================== 测试数据准备 ====================
@pytest.fixture
def setup_test_data():
    """插入测试数据到Neo4j"""
    with driver.session() as session:
        # 清理旧数据
        session.run("MATCH (c:Concept {name: '熵'}) DETACH DELETE c")
        # 创建测试数据
        session.run("CREATE (c:Concept {name: '熵', domain: '物理'})")
        session.run("""
            MATCH (c:Concept {name: '熵'})
            CREATE (r1:Concept {name: '信息熵', domain: '计算机'})
            CREATE (c)-[:RELATION {
                is_valid: true,
                relation: '信息熵借鉴热力学熵的概念',
                strength: 5,
                version: 1
            }]->(r1)

            CREATE (r2:Concept {name: '热力学第二定律', domain: '物理'})
            CREATE (c)-[:RELATION {
                is_valid: true,
                relation: '熵是热力学第二定律的核心物理量',
                strength: 5,
                version: 1
            }]->(r2)
        """)
    yield
    # 清理测试数据
    with driver.session() as session:
        session.run("MATCH (c:Concept {name: '熵'}) DETACH DELETE c")


# ==================== 运行测试 ====================
if __name__ == "__main__":
    pytest.main(["-v", __file__])