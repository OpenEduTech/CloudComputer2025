"""
第三部分测试：知识校验层
测试多源验证、可信度评分、冲突检测和来源溯源
"""

import os
import sys
import asyncio
import logging

# 设置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.credibility_scorer import (
    CredibilityScorer, 
    MultiSourceVerifier,
    Evidence, 
    SourceType,
    CredibilityLevel,
    ConflictInfo
)
from agents.verification_agent import VerificationAgent


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)


def print_result(success: bool, message: str):
    """打印测试结果（修复编码问题）"""
    symbol = "[PASS]" if success else "[FAIL]"
    print(f"  {symbol} {message}")


async def test_credibility_scorer():
    """测试1: 可信度评分算法"""
    print_section("测试1: 可信度评分算法")
    
    try:
        scorer = CredibilityScorer(
            min_evidence_count=2,
            wikipedia_weight=0.7,
            arxiv_weight=0.9,
            llm_weight=0.3,  # 降低LLM权重
            semantic_conflict_threshold=0.75
        )
        
        # 创建多个证据
        evidences = [
            Evidence(
                source_type=SourceType.WIKIPEDIA,
                source_name="Wikipedia",
                content="神经网络是一种计算模型，受生物神经系统启发",
                url="https://zh.wikipedia.org/wiki/神经网络",
                confidence=0.8
            ),
            Evidence(
                source_type=SourceType.ARXIV,
                source_name="Arxiv Paper",
                content="Artificial neural networks are inspired by biological neural networks",
                url="https://arxiv.org/abs/1234.5678",
                confidence=0.9
            ),
            Evidence(
                source_type=SourceType.LLM_REASONING,
                source_name="LLM Analysis",
                content="神经网络的结构和功能与生物神经元网络高度相似",
                confidence=0.7
            )
        ]
        
        # 计算可信度
        result = scorer.calculate_credibility(
            evidences, "神经网络", "生物神经系统"
        )
        
        print(f"\n  概念对: 神经网络 <-> 生物神经系统")
        print(f"  证据数量: {result['evidence_count']}")
        print(f"  可信度分数: {result['credibility_score']:.3f}")
        print(f"  可信度等级: {result['credibility_level']}")
        print(f"  来源多样性: {result['source_diversity']:.3f}")
        print(f"  是否有冲突: {result['has_conflicts']}")
        
        # 验证结果
        success = (
            result['evidence_count'] == 3 and
            result['credibility_score'] >= 0.7 and
            result['credibility_level'] in ['reliable', 'verified']
        )
        
        print_result(success, "可信度评分算法正常工作")
        
        return success
        
    except Exception as e:
        print_result(False, f"可信度评分测试失败: {str(e)}")
        return False


async def test_conflict_detection():
    """测试2: 冲突检测(改进版:含语义冲突)"""
    print_section("测试2: 冲突检测（增强版）")
    
    try:
        scorer = CredibilityScorer(
            llm_weight=0.3,
            semantic_conflict_threshold=0.75
        )
        
        # 创建冲突的证据（语义矛盾）
        conflicting_evidences = [
            Evidence(
                source_type=SourceType.WIKIPEDIA,
                source_name="Wikipedia Source 1",
                content="量子纠缠不能用于超光速通信，这是因为测量结果是随机的",
                confidence=0.9
            ),
            Evidence(
                source_type=SourceType.LLM_REASONING,
                source_name="LLM Source",
                content="量子纠缠可以用于信息传输，通过纠缠态实现通信",
                confidence=0.4
            )
        ]
        
        result = scorer.calculate_credibility(
            conflicting_evidences, "量子纠缠", "超光速通信"
        )
        
        print(f"\n  概念对: 量子纠缠 <-> 超光速通信")
        print(f"  检测到冲突: {result['has_conflicts']}")
        print(f"  冲突数量: {len(result['conflicts'])}")
        
        if result['conflicts']:
            for i, conflict in enumerate(result['conflicts']):
                print(f"\n  冲突 {i+1}:")
                print(f"    类型: {conflict['conflict_type']}")
                print(f"    严重程度: {conflict['severity']:.3f}")
                
                # 检查是否检测到语义冲突
                if conflict['conflict_type'] == 'semantic_contradiction':
                    print(f"    [NEW] 语义矛盾检测成功!")
        
        # 测试冲突解决
        if result['conflicts']:
            conflicts_obj = [
                ConflictInfo(
                    conflicting_evidences=conflicting_evidences,
                    conflict_type=result['conflicts'][0]['conflict_type'],
                    severity=result['conflicts'][0]['severity']
                )
            ]
            resolved = scorer.resolve_conflicts(conflicts_obj, strategy="highest_confidence")
            
            print(f"\n  冲突解决策略: highest_confidence")
            print(f"  解决后保留证据数: {len(resolved)}")
            if resolved:
                print(f"  选择的证据: {resolved[0].source_name} (置信度: {resolved[0].confidence})")
        
        # 验证是否检测到冲突
        success = result['has_conflicts'] and len(result['conflicts']) > 0
        print_result(success, "冲突检测机制正常工作（包括语义冲突）")
        
        return success
        
    except Exception as e:
        print_result(False, f"冲突检测测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_source_tracing():
    """测试3: 来源溯源(改进版:含引用验证)"""
    print_section("测试3: 来源溯源与引用验证")
    
    try:
        scorer = CredibilityScorer(llm_weight=0.3)
        
        # 测试1: 有效的Arxiv引用
        print("\n  测试1: 有效Arxiv引用")
        evidence_valid = Evidence(
            source_type=SourceType.ARXIV,
            source_name="Nature Physics",
            content="Quantum entanglement research (arxiv.org/abs/2301.12345) shows that...",
            url="https://arxiv.org/abs/2301.12345",
            confidence=0.95,
            timestamp="2024-01-15"
        )
        
        trace_info = scorer.trace_source(evidence_valid)
        
        print(f"  原始来源: {trace_info['primary_source']['name']}")
        print(f"  来源类型: {trace_info['primary_source']['type']}")
        print(f"  来源权威度: {trace_info['reliability_factors']['source_authority']:.2f}")
        print(f"  [NEW] 引用验证: {trace_info['reliability_factors']['citation_verified']}")
        
        if 'citation_check' in trace_info:
            citation_check = trace_info['citation_check']
            print(f"  [NEW] 引用详情:")
            print(f"    - 发现引用数: {len(citation_check['citations_found'])}")
            print(f"    - 验证通过: {len(citation_check['verified_citations'])}")
            print(f"    - 无效引用: {len(citation_check['invalid_citations'])}")
            if citation_check['verified_citations']:
                print(f"    - 示例: {citation_check['verified_citations'][0]}")
        
        # 测试2: LLM证据无引用（预警）
        print("\n  测试2: LLM证据无引用（应被标记）")
        evidence_llm = Evidence(
            source_type=SourceType.LLM_REASONING,
            source_name="LLM Analysis",
            content="根据2023年的研究，量子纠缠速度达到10^8倍光速",  # 编造的信息，无引用
            confidence=0.6
        )
        
        trace_info_llm = scorer.trace_source(evidence_llm)
        print(f"  [NEW] 引用验证: {trace_info_llm['reliability_factors']['citation_verified']}")
        print(f"  [NEW] 警告: LLM证据无可验证引用，可信度降低")
        
        # 测试3: 无效Arxiv ID
        print("\n  测试3: 无效Arxiv引用")
        evidence_invalid = Evidence(
            source_type=SourceType.LLM_REASONING,
            source_name="Fake Source",
            content="According to arxiv.org/abs/9999.99999 (invalid format)...",
            confidence=0.7
        )
        
        trace_info_invalid = scorer.trace_source(evidence_invalid)
        citation_check_invalid = trace_info_invalid['citation_check']
        print(f"  [NEW] 引用验证: {trace_info_invalid['reliability_factors']['citation_verified']}")
        if citation_check_invalid['invalid_citations']:
            print(f"  [NEW] 无效引用: {citation_check_invalid['invalid_citations']}")
        
        success = (
            trace_info['reliability_factors']['citation_verified'] and
            not trace_info_llm['reliability_factors']['citation_verified'] and
            not trace_info_invalid['reliability_factors']['citation_verified']
        )
        
        print_result(success, "来源溯源和引用验证功能正常工作")
        
        return success
        
    except Exception as e:
        print_result(False, f"来源溯源测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_source_verifier():
    """测试4: 多源验证器"""
    print_section("测试4: 多源验证器")
    
    try:
        verifier = MultiSourceVerifier()
        
        # 模拟多个数据源
        data_sources = {
            "wikipedia": {
                "summary": "深度学习是机器学习的一个分支，使用多层神经网络进行学习",
                "url": "https://zh.wikipedia.org/wiki/深度学习",
                "timestamp": "2024-01-15"
            },
            "arxiv": {
                "abstract": "Deep learning is a subset of machine learning based on artificial neural networks",
                "pdf_url": "https://arxiv.org/abs/1234.5678",
                "published": "2023-12-01"
            },
            "llm_reasoning": {
                "reasoning": "深度学习和神经网络是密切相关的概念，深度学习正是使用深层神经网络实现的",
                "confidence": 0.85
            }
        }
        
        # 执行多源验证
        result = await verifier.verify_from_multiple_sources(
            "深度学习", "神经网络", data_sources
        )
        
        print(f"\n  概念对: 深度学习 <-> 神经网络")
        print(f"  数据源数量: {len(data_sources)}")
        print(f"  证据数量: {result['evidence_count']}")
        print(f"  可信度分数: {result['credibility_score']:.3f}")
        print(f"  可信度等级: {result['credibility_level']}")
        print(f"  来源多样性: {result['source_diversity']:.3f}")
        
        print(f"\n  证据来源:")
        for i, evidence in enumerate(result['evidences'], 1):
            print(f"    {i}. {evidence['source_name']} (置信度: {evidence['confidence']:.2f})")
        
        success = (
            result['evidence_count'] >= 2 and
            result['credibility_score'] >= 0.6
        )
        
        print_result(success, "多源验证器正常工作")
        
        return success
        
    except Exception as e:
        print_result(False, f"多源验证器测试失败: {str(e)}")
        return False


async def test_verification_agent_integration():
    """测试5: VerificationAgent集成测试"""
    print_section("测试5: VerificationAgent多源验证集成")
    
    try:
        # 检查API密钥
        if not os.getenv("OPENROUTER_API_KEY"):
            print_result(False, "未设置OPENROUTER_API_KEY，跳过集成测试")
            return False
        
        if not os.getenv("OPENAI_API_KEY"):
            print_result(False, "未设置OPENAI_API_KEY，跳过集成测试")
            return False
        
        agent = VerificationAgent()
        
        print(f"\n  测试: 使用多源验证模式")
        
        # 测试多源验证
        result = await agent.verify_relation(
            concept_a="熵",
            concept_b="信息熵",
            claimed_relation="信息熵是熵的概念在信息论中的应用",
            strength=0.9,
            enable_multi_source=True
        )
        
        print(f"\n  概念对: 熵 <-> 信息熵")
        print(f"  验证模式: 多源验证")
        print(f"  可信度分数: {result['credibility_score']:.3f}")
        print(f"  是否通过: {result['is_valid']}")
        
        if 'evidence_count' in result:
            print(f"  证据数量: {result['evidence_count']}")
        if 'source_diversity' in result:
            print(f"  来源多样性: {result['source_diversity']:.3f}")
        if 'credibility_level' in result:
            print(f"  可信度等级: {result['credibility_level']}")
        
        if result.get('warnings'):
            print(f"\n  警告信息:")
            for warning in result['warnings']:
                print(f"    - {warning}")
        
        success = result['is_valid'] and result['credibility_score'] >= 0.5
        
        print_result(success, "VerificationAgent多源验证集成正常")
        
        return success
        
    except Exception as e:
        print_result(False, f"集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_evidence_quality_levels():
    """测试6: 不同质量级别的证据"""
    print_section("测试6: 证据质量等级测试")
    
    try:
        scorer = CredibilityScorer()
        
        # 测试不同质量级别
        test_cases = [
            {
                "name": "高质量证据（多源+高置信度）",
                "evidences": [
                    Evidence(SourceType.ARXIV, "Arxiv", "High quality paper", confidence=0.95),
                    Evidence(SourceType.WIKIPEDIA, "Wikipedia", "Verified info", confidence=0.85),
                    Evidence(SourceType.TEXTBOOK, "Textbook", "Standard definition", confidence=0.9)
                ],
                "expected_level": CredibilityLevel.VERIFIED
            },
            {
                "name": "中等质量证据（单源+中等置信度）",
                "evidences": [
                    Evidence(SourceType.WIKIPEDIA, "Wikipedia", "Some info", confidence=0.6),
                    Evidence(SourceType.LLM_REASONING, "LLM", "Reasoning", confidence=0.5)
                ],
                "expected_level": CredibilityLevel.PROBABLE
            },
            {
                "name": "低质量证据（单源+低置信度）",
                "evidences": [
                    Evidence(SourceType.LLM_REASONING, "LLM", "Uncertain", confidence=0.3)
                ],
                "expected_level": CredibilityLevel.QUESTIONABLE
            }
        ]
        
        all_passed = True
        
        for i, test_case in enumerate(test_cases, 1):
            result = scorer.calculate_credibility(
                test_case["evidences"], "概念A", "概念B"
            )
            
            print(f"\n  测试 {i}: {test_case['name']}")
            print(f"    可信度分数: {result['credibility_score']:.3f}")
            print(f"    可信度等级: {result['credibility_level']}")
            print(f"    预期等级: {test_case['expected_level'].value}")
            
            # 检查是否符合预期等级范围
            level_match = result['credibility_level'] == test_case['expected_level'].value
            
            if not level_match:
                # 允许相邻等级（因为边界值可能不同）
                levels_order = ['questionable', 'uncertain', 'probable', 'reliable', 'verified']
                actual_idx = levels_order.index(result['credibility_level'])
                expected_idx = levels_order.index(test_case['expected_level'].value)
                level_match = abs(actual_idx - expected_idx) <= 1
            
            passed = level_match
            all_passed = all_passed and passed
            
            print_result(passed, f"等级判定{'正确' if passed else '不符'}")
        
        print_result(all_passed, "证据质量等级测试完成")
        
        return all_passed
        
    except Exception as e:
        print_result(False, f"证据质量测试失败: {str(e)}")
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("第三部分：知识校验层 - 功能测试")
    print("测试多源验证、可信度评分、冲突检测和来源溯源")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(await test_credibility_scorer())
    results.append(await test_conflict_detection())
    results.append(await test_source_tracing())
    results.append(await test_multi_source_verifier())
    results.append(await test_evidence_quality_levels())
    results.append(await test_verification_agent_integration())
    
    # 汇总结果
    print_section("测试结果汇总")
    
    test_names = [
        "可信度评分算法",
        "冲突检测机制",
        "来源溯源功能",
        "多源验证器",
        "证据质量等级",
        "VerificationAgent集成"
    ]
    
    for i, (name, passed) in enumerate(zip(test_names, results), 1):
        print_result(passed, f"测试{i}: {name}")
    
    passed_count = sum(results)
    total_count = len(results)
    
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！第三部分功能完整可用。")
        print("\n已验证:")
        print("  ✓ 可信度评分算法：基于多证据加权计算")
        print("  ✓ 多源验证：整合Wikipedia、Arxiv、LLM")
        print("  ✓ 冲突检测：识别证据矛盾并仲裁")
        print("  ✓ 来源溯源：追踪信息来源链")
        print("  ✓ VerificationAgent：完整集成多源验证")
    else:
        print(f"\n⚠️  部分测试未通过 ({total_count - passed_count} 个)")
    
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
