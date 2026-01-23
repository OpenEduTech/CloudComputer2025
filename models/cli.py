import sys
import json
from typing import Optional, List, Dict
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
import questionary
from models import Question, EvaluationResult

class InteractiveCLI:
    """交互式命令行界面"""
    
    def __init__(self, agent):
        self.agent = agent
        self.console = Console()
        self.current_user = None
        self.current_session = None
    
    def run(self):
        """运行主界面"""
        self._show_welcome()
        
        while True:
            choice = self._main_menu()
            
            if choice == "1":
                self._start_new_session()
            elif choice == "2":
                self._review_wrong_questions()
            elif choice == "3":
                self._view_statistics()
            elif choice == "4":
                self._analyze_weaknesses()
            elif choice == "5":
                self._manage_materials()
            elif choice == "6":
                self.console.print("[bold green]感谢使用，再见！[/bold green]")
                break
            else:
                self.console.print("[red]无效选择，请重试[/red]")
    
    def _show_welcome(self):
        """显示欢迎信息"""
        welcome_text = """
        LLMAgent 学习评估系统
        
        基于AI的个性化学习评估和巩固系统
        特点：
        • 自动生成评估题目
        • 智能判卷与详细解析
        • 个性化弱点分析
        • 错题本与学习建议
        """
        
        self.console.print(Panel(welcome_text, title="欢迎", border_style="cyan"))
    
    def _main_menu(self) -> str:
        """显示主菜单"""
        choice = questionary.select(
            "主菜单 - 请选择 (Use arrow keys)",
            choices=[
                "1. 开始新的学习评估",
                "2. 复习错题本",
                "3. 查看学习统计",
                "4. 弱点分析报告",
                "5. 管理学习资料",
                "6. 退出系统"
            ],
            default="1. 开始新的学习评估",
        ).ask()
        
        # 提取选项编号
        return choice.split(".")[0].strip()
    
    def _start_new_session(self):
        """开始新的学习评估会话"""
        # 选择或输入用户ID
        if not self.current_user:
            self.current_user = questionary.text("请输入用户ID", default="default_user").ask()
        
        # 选择学习资料
        material_choice = self._select_material()
        if not material_choice:
            return
        
        # 配置评估参数
        config = self._configure_session()
        
        # 处理学习资料
        self.console.print("[cyan]处理学习资料...[/cyan]")
        try:
            chunks = self.agent.process_material(material_choice)
        except Exception as e:
            self.console.print(f"[red]处理资料失败: {e}[/red]")
            raise e
            return
        
        # 根据配置选择是否使用流式生成题目
        questions = []
        if self.agent.config.ENABLE_STREAM:
            self._generate_questions_with_stream(
                chunks,
                num_questions=config["num_questions"],
                question_types=config.get("question_types"),
                difficulty_mix=config["difficulty_mix"],
                questions_list=questions
            )
        else:
            self._generate_questions_without_stream(
                chunks,
                num_questions=config["num_questions"],
                question_types=config.get("question_types"),
                difficulty_mix=config["difficulty_mix"],
                questions_list=questions
            )
        
        session_results = []
        for i, question in enumerate(questions, 1):
            self.console.clear()
            self.console.print(f"\n[bold]题目 {i}/{len(questions)}[/bold]")
            self.console.print(f"[dim]难度: {question.difficulty}[/dim]")
            
            # 显示题目
            self._display_question(question)
            
            # 获取用户答案
            user_answer = self._get_user_answer(question)
            
            # 评估答案
            evaluation = self.agent.evaluate_answer(question, user_answer)
            
            # 显示结果
            self._display_evaluation(question, user_answer, evaluation)
            
            # 保存结果
            self.agent.save_performance(
                self.current_user, 
                question, 
                evaluation, 
                user_answer
            )
            
            session_results.append({
                "question": question.content,
                "user_answer": user_answer,
                "evaluation": evaluation,
                "correct": evaluation.is_correct
            })
            
            # 询问是否继续
            if i < len(questions):
                if not Confirm.ask("继续下一题？", default=True):
                    break
        
        # 显示会话总结
        self._show_session_summary(session_results)
    
    def _display_question(self, question: Question):
        """显示题目"""
        self.console.print(f"\n[bold yellow]{question.content}[/bold yellow]\n")
        
        if question.question_type == "multiple_choice":
            for idx, option in enumerate(question.options, 1):
                self.console.print(f"  {idx}. {option}")
            self.console.print()
    
    def _get_user_answer(self, question: Question) -> str:
        """获取用户答案"""
        if question.question_type == "multiple_choice":
            choices = question.options
            choice = questionary.select(
                "请选择答案：",
                choices=choices
            ).ask()
            # 转换为选项文本
            return choice
        elif question.question_type == "true_false":
            choice = questionary.select(
                "请选择：",
                choices=["True", "False"],
                default="True"
            ).ask()
            return choice
        else:
            self.console.print("[dim]请输入你的答案[/dim]")
            self.console.print("[yellow]输入完毕后，按 Ctrl+D (Mac: Cmd+D) 或 Ctrl+Z (Windows) 结束输入[/yellow]\n")
            
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            
            answer = "\n".join(lines).strip()
            if not answer:
                self.console.print("[red]警告：您没有输入任何内容！[/red]")
            return answer
    
    def _display_evaluation(self, question: Question, user_answer: str, evaluation: EvaluationResult):
        """显示评估结果"""
        self.console.print("\n" + "="*50)
        
        if evaluation.is_correct:
            self.console.print("[bold green]✓ 回答正确！[/bold green]")
        else:
            self.console.print("[bold red]✗ 回答错误[/bold red]")
        
        self.console.print(f"[bold]得分: {evaluation.score}/100[/bold]")
        
        if not evaluation.is_correct:
            self.console.print(f"\n[bold]你的答案:[/bold] {user_answer[:100]}...")
            self.console.print(f"[bold]正确答案:[/bold] {question.correct_answer[:100]}...")
        
        self.console.print(f"\n[bold]详细解析:[/bold]")
        self.console.print(Panel(evaluation.detailed_explanation, border_style="blue"))
        
        if evaluation.suggested_improvement:
            self.console.print(f"\n[bold cyan]改进建议:[/bold cyan]")
            self.console.print(evaluation.suggested_improvement)
        
        if evaluation.mistakes:
            self.console.print(f"\n[bold yellow]错误点:[/bold yellow]")
            for mistake in evaluation.mistakes:
                self.console.print(f"  • {mistake}")
    
    def _show_session_summary(self, results: List[Dict]):
        """显示会话总结"""
        correct_count = sum(1 for r in results if r["correct"])
        total_score = sum(r["evaluation"].score for r in results)
        avg_score = total_score / len(results) if results else 0
        
        summary = Table(title="本次评估总结", box=None)
        summary.add_column("指标", style="cyan")
        summary.add_column("数值", style="white")
        
        summary.add_row("总题数", str(len(results)))
        summary.add_row("正确题数", f"{correct_count} ({correct_count/len(results)*100:.1f}%)")
        summary.add_row("平均得分", f"{avg_score:.1f}/100")
        
        self.console.print("\n")
        self.console.print(Panel(summary, title="评估完成", border_style="green"))
        
        # 显示建议
        if avg_score < 70:
            self.console.print("\n[bold yellow]建议：[/bold yellow]基础需要加强，建议系统复习相关概念")
        elif avg_score < 90:
            self.console.print("\n[bold green]建议：[/bold green]表现良好，可以挑战更高难度")
        else:
            self.console.print("\n[bold blue]建议：[/bold blue]优秀！可以开始学习新内容")
    
    def _review_wrong_questions(self):
        """复习错题本"""
        if not self.current_user:
            self.current_user = questionary.text("请输入用户ID", default="default_user").ask()
        
        self.console.print("[cyan]加载错题...[/cyan]")
        wrong_questions = self.agent.get_wrong_questions(self.current_user)
        
        if not wrong_questions:
            self.console.print("[yellow]暂无错题记录[/yellow]")
            return
        
        self.console.print(f"\n[bold]找到 {len(wrong_questions)} 道错题[/bold]")
        
        for i, wq in enumerate(wrong_questions[:10], 1):  # 最多显示10道
            self.console.print(f"\n[bold]{i}. {wq['question']}[/bold]")
            self.console.print(f"[dim]错误次数: {wq.get('wrong_count', 1)}[/dim]")
            
            if input("按Enter查看答案，或输入q退出：").lower() == 'q':
                break
            
            self.console.print(f"\n[green]正确答案:[/green] {wq['correct_answer']}")
            self.console.print(f"[red]你的答案:[/red] {wq.get('user_answer', '无')}")
            
            if 'detailed_explanation' in wq:
                self.console.print(f"\n[blue]解析:[/blue] {wq['detailed_explanation']}")
    
    def _view_statistics(self):
        """查看学习统计"""
        if not self.current_user:
            self.current_user = questionary.text("请输入用户ID", default="default_user").ask()
        
        self.console.print("[cyan]生成统计报告...[/cyan]")
        stats = self.agent.get_user_statistics(self.current_user)
        
        self.console.print("\n[bold cyan]学习统计报告[/bold cyan]")
        self.console.print("="*50)
        
        table = Table(box=None)
        table.add_column("统计项", style="cyan")
        table.add_column("数值", style="white")
        
        table.add_row("总答题数", str(stats["total_attempts"]))
        table.add_row("正确答题数", str(stats["correct_attempts"]))
        table.add_row("总体准确率", f"{stats['overall_accuracy']*100:.1f}%")
        table.add_row("未掌握错题数", str(stats["wrong_questions_count"]))
        
        self.console.print(table)
        
        # 显示难度统计
        if stats.get("difficulty_stats"):
            self.console.print("\n[bold]难度分布统计[/bold]")
            diff_table = Table(box=None)
            diff_table.add_column("难度", style="cyan")
            diff_table.add_column("答题数", style="white")
            diff_table.add_column("准确率", style="white")
            
            for diff, diff_stats in stats["difficulty_stats"].items():
                diff_table.add_row(
                    diff,
                    str(diff_stats["total"]),
                    f"{diff_stats['accuracy']*100:.1f}%"
                )
            
            self.console.print(diff_table)
    
    def _analyze_weaknesses(self):
        """弱点分析"""
        if not self.current_user:
            self.current_user = questionary.text("请输入用户ID", default="default_user").ask()
        
        self.console.print("[cyan]分析学习弱点...[/cyan]")
        analysis = self.agent.analyze_weaknesses(self.current_user)
        
        self.console.print("\n[bold red]弱点分析报告[/bold red]")
        self.console.print("="*50)
        
        if analysis["weaknesses"]:
            self.console.print(f"\n发现 {len(analysis['weaknesses'])} 个需要改进的方面：\n")
            
            for weakness in analysis["weaknesses"]:
                self.console.print(f"[bold]{weakness['tag']}[/bold]")
                self.console.print(f"  准确率: {weakness['accuracy']}%")
                self.console.print(f"  答题数: {weakness['total_attempts']}")
                
                if weakness.get("error_questions"):
                    self.console.print(f"  典型错题: {len(weakness['error_questions'])} 道")
                
                self.console.print()
        
        if analysis.get("recommendations"):
            self.console.print("[bold cyan]学习建议：[/bold cyan]")
            for rec in analysis["recommendations"][:5]:  # 最多显示5条建议
                self.console.print(f"  • {rec}")
    
    def _select_material(self) -> Optional[str]:
        """选择学习资料"""
        choices = questionary.select(
            "选择学习资料输入方式：",
            choices=[
                "输入文本",
                "PDF文件路径",
                "使用示例资料",
                "返回"
            ]
        ).ask()
        
        if choices == "返回":
            return None
        elif choices == "输入文本":
            self.console.print("[dim]请输入学习内容（按Ctrl+D结束输入）：[/dim]")
            
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            
            return "\n".join(lines)
        elif choices == "PDF文件路径":
            path = questionary.text("请输入PDF文件路径").ask()
            return {"path": path, "type": "pdf"}
        else:  # 示例资料
            return self._get_sample_material()
    
    def _configure_session(self) -> Dict:
        """配置评估会话"""
        num_questions = int(questionary.select(
            "题目数量", 
            choices=["3", "5", "10", "15"],
            default="5"
        ).ask())
        
        question_types = questionary.select(
            "题目类型选择：",
            choices=[
                "混合类型（所有类型）",
                "选择题（Multiple Choice）",
                "简答题（Short Answer）",
                "真假题（True/False）"
            ],
            default="混合类型（所有类型）"
        ).ask()
        
        # 将选择映射到实际的类型列表
        type_mapping = {
            "混合类型（所有类型）": ["multiple_choice", "short_answer", "true_false"],
            "选择题（Multiple Choice）": ["multiple_choice"],
            "简答题（Short Answer）": ["short_answer"],
            "真假题（True/False）": ["true_false"]
        }
        selected_types = type_mapping[question_types]
        
        difficulty = questionary.select(
            "难度设置：",
            choices=[
                "自适应难度",
                "简单为主",
                "中等难度",
                "挑战难度",
                "混合难度"
            ],
            default="自适应难度"
        ).ask()
        
        return {
            "num_questions": num_questions,
            "question_types": selected_types,
            "difficulty_mix": difficulty
        }
    
    def _generate_questions_without_stream(
        self,
        chunks,
        num_questions: int = 5,
        question_types=None,
        difficulty_mix: str = "adaptive",
        questions_list=None
    ):
        """不使用流式方式生成题目（普通模式）"""
        if questions_list is None:
            questions_list = []
        
        self.console.print(f"[cyan]生成 {num_questions} 道题目...[/cyan]")
        
        # 直接调用 agent 的非流式生成方法
        questions = self.agent.generate_questions(
            chunks,
            num_questions=num_questions,
            question_types=question_types,
            difficulty_mix=difficulty_mix
        )
        
        questions_list.extend(questions)
    
    def _generate_questions_with_stream(
        self,
        chunks,
        num_questions: int = 5,
        question_types=None,
        difficulty_mix: str = "adaptive",
        questions_list=None
    ):
        """使用流式方式生成题目并实时显示"""
        if questions_list is None:
            questions_list = []
        
        def on_question_start(current, total):
            """题目开始生成时的回调"""
            self.console.print(f"\n[bold cyan]生成题目 {current}/{total}...[/bold cyan]")
        
        def on_question_chunk(chunk_text):
            """流式接收内容时的回调"""
            # 实时显示流式内容
            self.console.print(chunk_text, end="", soft_wrap=True)
        
        def on_question_complete(question):
            """题目生成完成时的回调"""
            self.console.print()  # 换行
            self.console.print(f"[bold green]✓ 题目 {question.question_id} 已生成[/bold green]")
            questions_list.append(question)
        
        # 调用agent的流式生成方法
        self.agent.generate_questions_stream(
            chunks,
            num_questions=num_questions,
            question_types=question_types,
            difficulty_mix=difficulty_mix,
            on_question_start=on_question_start,
            on_question_chunk=on_question_chunk,
            on_question_complete=on_question_complete
        )
    
    def _get_sample_material(self) -> str:
        """获取示例学习资料"""
        return """机器学习基础概念

1. 监督学习
监督学习是指从标记的训练数据中学习一个模型，然后根据这个模型对新的数据进行预测。常见的监督学习算法包括线性回归、逻辑回归、决策树、支持向量机等。

2. 无监督学习
无监督学习是指从无标记的数据中寻找隐藏的结构或模式。常见的无监督学习算法包括聚类（如K-means）、降维（如PCA）和关联规则学习。

3. 过拟合与欠拟合
过拟合是指模型在训练数据上表现很好，但在新数据上表现不佳。欠拟合是指模型在训练数据和新数据上都表现不佳。解决过拟合的方法包括正则化、增加训练数据、减少模型复杂度等。

4. 交叉验证
交叉验证是一种评估模型性能的技术，它将数据集分成多个子集，轮流将其中一个子集作为测试集，其余作为训练集。常用的有k折交叉验证。

5. 评估指标
分类问题常用准确率、精确率、召回率、F1分数等指标。回归问题常用均方误差（MSE）、平均绝对误差（MAE）、R²分数等指标。"""
    
    def _manage_materials(self):
        """管理学习资料"""
        self.console.print("[yellow]学习资料管理功能开发中...[/yellow]")