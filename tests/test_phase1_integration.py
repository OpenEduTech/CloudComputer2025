"""
阶段一集成测试 - 验证Agent编排系统完整性
测试内容：
1. 模块导入测试
2. 数据模型验证
3. Prompt模板测试
4. Agent初始化测试
5. 编排器工作流测试（无需真实API调用）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试1: 验证所有关键模块可以正常导入"""
    print("\n" + "="*60)
    print("测试1: 模块导入测试")
    print("="*60)
    
    try:
        # 测试shared模块
        print("✓ 导入 shared.constants...")
        from shared.constants import Discipline, RelationType, AgentConfig
        
        print("✓ 导入 shared.error_codes...")
        from shared.error_codes import ErrorCode
        
        print("✓ 导入 shared.utils...")
        from shared.utils import generate_request_id, generate_node_id, validate_disciplines
        
        print("✓ 导入 shared.schemas...")
        from shared.schemas import ConceptNode, ConceptEdge, APIResponse, GraphData, Metadata
        
        # 测试prompt模块
        print("✓ 导入 prompts...")
        from prompts import DiscoveryPrompt, VerificationPrompt, GraphPrompt
        
        # 测试agent模块
        print("✓ 导入 agents...")
        from agents import ConceptDiscoveryAgent, VerificationAgent, GraphBuilderAgent, get_orchestrator
        
        print("\n✅ 所有模块导入成功！")
        return True
        
    except ImportError as e:
        print(f"\n❌ 导入失败: {e}")
        return False


def test_data_models():
    """测试2: 验证数据模型定义"""
    print("\n" + "="*60)
    print("测试2: 数据模型验证")
    print("="*60)
    
    try:
        from shared.schemas import ConceptNode, ConceptEdge, GraphData, Metadata
        from shared.constants import Discipline, RelationType
        
        # 测试ConceptNode
        print("✓ 创建 ConceptNode...")
        node = ConceptNode(
            id="test_node_001",
            label="熵",
            discipline="物理学",
            definition="系统无序程度的度量",
            credibility=0.95,
            metadata={"context": "热力学第二定律"}
        )
        print(f"  节点ID: {node.id}, 名称: {node.label}")
        
        # 测试ConceptEdge
        print("✓ 创建 ConceptEdge...")
        edge = ConceptEdge(
            source="test_node_001",
            target="test_node_002",
            relation=RelationType.IS_FOUNDATION_OF,
            weight=0.85,
            reasoning="熵是信息论的基础概念"
        )
        print(f"  边类型: {edge.relation}, 强度: {edge.weight}")
        
        # 测试GraphData
        print("✓ 创建 GraphData...")
        metadata = Metadata(
            total_nodes=1,
            total_edges=1,
            verified_nodes=1,
            avg_credibility=0.95,
            processing_time=0.1
        )
        graph = GraphData(
            nodes=[node],
            edges=[edge],
            metadata=metadata
        )
        print(f"  图节点数: {len(graph.nodes)}, 边数: {len(graph.edges)}")
        
        print("\n✅ 数据模型验证通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 数据模型验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompts():
    """测试3: 验证Prompt模板"""
    print("\n" + "="*60)
    print("测试3: Prompt模板测试")
    print("="*60)
    
    try:
        from prompts import DiscoveryPrompt, VerificationPrompt, GraphPrompt
        from shared.constants import Discipline
        
        # 测试发现Prompt
        print("✓ 测试 DiscoveryPrompt...")
        discovery_prompt = DiscoveryPrompt.get_discovery_prompt(
            concept="熵",
            disciplines=[Discipline.PHYSICS, Discipline.COMPUTER],
            depth=2
        )
        assert len(discovery_prompt) > 100, "Discovery prompt太短"
        assert "熵" in discovery_prompt, "Prompt中未包含目标概念"
        print(f"  生成的Prompt长度: {len(discovery_prompt)} 字符")
        
        # 测试验证Prompt
        print("✓ 测试 VerificationPrompt...")
        verify_prompt = VerificationPrompt.get_verification_prompt(
            concept_a="熵",
            concept_b="信息量",
            claimed_relation="is_foundation_of",
            strength=0.85
        )
        assert len(verify_prompt) > 100, "Verification prompt太短"
        assert "熵" in verify_prompt and "信息量" in verify_prompt
        print(f"  生成的Prompt长度: {len(verify_prompt)} 字符")
        
        # 测试图构建Prompt
        print("✓ 测试 GraphPrompt...")
        mock_concepts = [
            {"name": "熵", "disciplines": ["物理学"], "strength": 0.9},
            {"name": "信息量", "disciplines": ["计算机科学"], "strength": 0.85}
        ]
        graph_prompt = GraphPrompt.get_graph_builder_prompt(
            verified_concepts=mock_concepts
        )
        assert len(graph_prompt) > 100, "Graph prompt太短"
        assert "熵" in graph_prompt
        print(f"  生成的Prompt长度: {len(graph_prompt)} 字符")
        
        print("\n✅ Prompt模板测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ Prompt测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """测试4: 验证Agent初始化"""
    print("\n" + "="*60)
    print("测试4: Agent初始化测试")
    print("="*60)
    
    try:
        from agents import ConceptDiscoveryAgent, VerificationAgent, GraphBuilderAgent
        from agents.llm_client import LLMClient
        
        # 创建模拟的LLM客户端（不需要真实API key）
        print("✓ 创建 LLMClient（模拟模式）...")
        llm_client = LLMClient(
            api_key="test_key_for_initialization",
            model="google/gemini-3-pro-preview",
            timeout=30
        )
        print(f"  模型: {llm_client.model}")
        
        # 初始化各个Agent（不需要传参，他们内部创建llm_client）
        print("✓ 初始化 ConceptDiscoveryAgent...")
        discovery_agent = ConceptDiscoveryAgent()
        print("  ✓ ConceptDiscoveryAgent 初始化成功")
        
        print("✓ 初始化 VerificationAgent...")
        verification_agent = VerificationAgent()
        print("  ✓ VerificationAgent 初始化成功")
        
        print("✓ 初始化 GraphBuilderAgent...")
        graph_agent = GraphBuilderAgent()
        print("  ✓ GraphBuilderAgent 初始化成功")
        
        print("\n✅ Agent初始化测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orchestrator():
    """测试5: 验证编排器结构"""
    print("\n" + "="*60)
    print("测试5: 编排器结构测试")
    print("="*60)
    
    try:
        from agents import get_orchestrator
        from shared.constants import Discipline
        
        # 获取编排器（使用环境变量中的API key）
        print("✓ 获取 AgentOrchestrator...")
        # get_orchestrator不接受参数，从环境变量读取
        orchestrator = get_orchestrator()
        
        # 验证编排器拥有所有必需的方法
        print("✓ 验证编排器方法...")
        required_methods = ['discover', 'verify', 'expand']
        for method_name in required_methods:
            assert hasattr(orchestrator, method_name), f"缺少方法: {method_name}"
            print(f"  ✓ 方法存在: {method_name}")
        
        # 验证编排器拥有3个agent
        print("✓ 验证Agent配置...")
        assert hasattr(orchestrator, 'discovery_agent'), "缺少 discovery_agent"
        assert hasattr(orchestrator, 'verification_agent'), "缺少 verification_agent"
        assert hasattr(orchestrator, 'graph_builder_agent'), "缺少 graph_builder_agent"
        print("  ✓ 所有Agent已配置")
        
        print("\n✅ 编排器结构测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 编排器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_files():
    """测试6: 验证配置文件"""
    print("\n" + "="*60)
    print("测试6: 配置文件验证")
    print("="*60)
    
    try:
        # 检查.env.example
        env_example = project_root / ".env.example"
        print(f"✓ 检查 .env.example...")
        assert env_example.exists(), ".env.example文件不存在"
        content = env_example.read_text(encoding='utf-8')
        assert "OPENROUTER_API_KEY" in content, "缺少OPENROUTER_API_KEY配置"
        assert "google/gemini-3-pro-preview" in content, "缺少模型配置"
        print("  ✓ .env.example配置完整")
        
        # 检查agents/config.yaml
        config_yaml = project_root / "agents" / "config.yaml"
        print(f"✓ 检查 agents/config.yaml...")
        assert config_yaml.exists(), "config.yaml文件不存在"
        content = config_yaml.read_text(encoding='utf-8')
        assert "gemini-3-pro" in content, "缺少模型配置"
        print("  ✓ config.yaml配置完整")
        
        # 检查prompts/prompt_config.json
        prompt_config = project_root / "prompts" / "prompt_config.json"
        print(f"✓ 检查 prompts/prompt_config.json...")
        assert prompt_config.exists(), "prompt_config.json文件不存在"
        print("  ✓ prompt_config.json存在")
        
        print("\n✅ 配置文件验证通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 配置文件验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_documentation():
    """测试7: 验证文档完整性"""
    print("\n" + "="*60)
    print("测试7: 文档完整性检查")
    print("="*60)
    
    try:
        docs_dir = project_root / "docs"
        required_docs = [
            "agent-design.md",
            "prompt-templates.md",
            "api-agent.md"
        ]
        
        for doc_name in required_docs:
            doc_path = docs_dir / doc_name
            print(f"✓ 检查 {doc_name}...")
            assert doc_path.exists(), f"{doc_name} 不存在"
            content = doc_path.read_text(encoding='utf-8')
            assert len(content) > 500, f"{doc_name} 内容过少"
            print(f"  ✓ {doc_name} 存在且内容充实 ({len(content)} 字符)")
        
        print("\n✅ 文档完整性检查通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 文档检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("ConceptGraph AI - 阶段一集成测试")
    print("测试范围: Agent编排系统完整性")
    print("="*60)
    
    results = {
        "模块导入": test_imports(),
        "数据模型": test_data_models(),
        "Prompt模板": test_prompts(),
        "Agent初始化": test_agent_initialization(),
        "编排器结构": test_orchestrator(),
        "配置文件": test_config_files(),
        "文档完整性": test_documentation()
    }
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s}: {status}")
    
    print("\n" + "="*60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("="*60)
        print("🎉 恭喜！阶段一所有测试通过，代码可以提交！")
        print("="*60)
        print("\n建议的Git提交命令:")
        print("git add .")
        print("git commit -m 'feat(agent): 完成阶段一-智能体编排系统(OpenRouter+Gemini3Pro)'")
        print("git push origin feature/agent-system")
        return 0
    else:
        print("="*60)
        print("⚠️  部分测试失败，请修复后再提交")
        print("="*60)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
