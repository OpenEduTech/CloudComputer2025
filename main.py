from models.config import Config
from models.agent import LLMAgent
from models.cli import InteractiveCLI


def main():
    """ 主程序入口函数 """
    try:
        config = Config()
        agent = LLMAgent(config)
        cli = InteractiveCLI(agent)
        cli.run()
        agent.cleanup()
        
    except KeyboardInterrupt:
        print("\n程序被中断")
    except Exception as e:
        print(f"程序出错: {e}")
        raise

if __name__ == "__main__":
    main()
