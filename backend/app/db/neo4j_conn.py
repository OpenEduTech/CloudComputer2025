from neo4j import GraphDatabase, Driver
import os
import time

# 全局Driver实例（你的定义是对的）
driver: Driver = None


def init_neo4j(max_retries=5, retry_interval=5):
    """初始化Neo4j连接（新增重试逻辑）"""
    global driver
    # 如果已有有效驱动，直接返回（避免重复创建）
    if driver is not None:
        try:
            driver.verify_connectivity()
            print("✅ 现有Neo4j驱动有效")
            return driver
        except:
            print("⚠️ 现有驱动失效，重新初始化...")
            driver = None

    try:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")

        if not all([uri, user, password]):
            raise Exception("Neo4j配置未完善")

        # 重试连接（解决Neo4j启动慢的问题）
        for retry in range(max_retries):
            try:
                driver = GraphDatabase.driver(uri, auth=(user, password))
                driver.verify_connectivity()
                print(f"✅ 第{retry+1}次尝试：Neo4j连接成功")
                return driver
            except Exception as e:
                print(f"❌ 第{retry+1}次尝试：Neo4j连接失败 - {e}")
                if retry == max_retries - 1:
                    driver = None
                    raise
                time.sleep(retry_interval)
    except Exception as e:
        print(f"Neo4j连接最终失败：{e}")
        driver = None


def get_neo4j_driver():
    """
    统一获取驱动的入口（核心修复）
    - 每次调用都检查驱动是否有效
    - 无效则重新初始化
    """
    global driver
    if driver is None:
        init_neo4j()  # 驱动为None时，重新初始化
    return driver


def close_neo4j():
    """关闭Neo4j连接"""
    global driver
    if driver:
        driver.close()
        driver = None
        print("Neo4j连接已关闭")

# ========== 关键修改：删除模块导入时的自动执行 ==========
# 原代码：init_neo4j() → 过早执行，失败后无重试
# 改为：只在需要时调用get_neo4j_driver()初始化
# init_neo4j()  # 注释掉这行！
# print(driver)  # 注释掉这行！