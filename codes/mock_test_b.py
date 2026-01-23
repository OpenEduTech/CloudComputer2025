import os
from models import NewsItem, SourceType, ReportSnapshot
from incremental_analysis import incremental_compare, generate_global_summary
from conflict_resolution import resolve_conflicts

# 配置 API Key
os.environ["SILICONFLOW_API_KEY"] = "sk-zieigdeeconidojrwencrdvsejqfxaoqvbxeqbsrxmqinlna"

def run_debug_session():
    print("=== [成员 B 调试模式] 纯模拟全链路逻辑测试 ===\n")

    # 1. 模拟旧快照内容
    old_snapshot = ReportSnapshot(
        keyword="综合行业",
        collected_at="2026-01-19_100000",
        items=[
            NewsItem(
                title="基准数据",
                content="产能利用率为 80%，全固态电池研发处于实验室阶段。",
                source=SourceType.OFFICIAL
            )
        ]
    )

    # 2. 模拟新资讯内容
    new_items = [
        NewsItem(
            title="制造端动态",
            content="产线稼动率已由 80% 攀升至 92%，原材料单价调涨至 1850元/吨。",
            source=SourceType.MEDIA,
            published_at="2026-01-20"
        ),
        NewsItem(
            title="前沿技术突破",
            content="全固态电池已从实验室转入样件装车路测阶段，商用化进度超预期。",
            source=SourceType.MEDIA,
            published_at="2026-01-20"
        )
    ]

    # 3. 运行核心逻辑链
    
    # 步骤 A: 提取差异 (AI)
    print("--- 步骤 1: 正在进行语义增量对比 ---")
    changes = incremental_compare(old_snapshot, new_items)
    
    # 步骤 B: 冲突仲裁
    print("--- 步骤 2: 正在进行冲突仲裁 ---")
    decisions = resolve_conflicts(changes)

    # 步骤 C: 生成“总的最终决策” (AI 聚合)
    print("--- 步骤 3: 正在生成全局总决策 ---\n")
    global_summary = generate_global_summary("综合行业", decisions)

    # 4. 格式化输出结果
    print("="*60)
    print("【🌟 今日行研雷达：总的最终决策】")
    print(f"{global_summary}")
    print("="*60)

    print("\n【📊 详细指标变动明细】")
    for d in decisions:
        print(f"● 指标：{d.field}")
        print(f"  当前值：{d.final_value}")
        print(f"  分析建议：{d.reason}") # 这里的 reason 已经是 AI 生成的“人话”分析
        print("-" * 40)

    print("\n=== 调试结束 ===")

if __name__ == "__main__":
    run_debug_session()