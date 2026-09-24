import argparse
import asyncio

from dotenv import load_dotenv
from browser_use import Agent, Browser, ChatOpenAI, ChatAnthropic

# Load environment variables
load_dotenv()

def build_llm(model: str):
    if model.startswith("claude"):
        return ChatAnthropic(model=model)
    return ChatOpenAI(model=model)


async def main(task: str, model: str, max_steps: int = 20) -> None:
    llm = build_llm(model)

    browser = Browser(
        cdp_url="http://localhost:9222",
        minimum_wait_page_load_time=2.0,
        wait_for_network_idle_page_load_time=2.0,
        wait_between_actions=2.0,
    )

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
    )

    try:
        history = await agent.run(max_steps=max_steps)
        result = history.final_result()
        success = history.is_done()
        print(f"Result: {result}")
        print(f"Task completed. Success: {success}")
    finally:
        try:
            await asyncio.wait_for(browser.stop(), timeout=10.0)
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a browser-use agent task")
    parser.add_argument("--task", help="Task for the agent to execute", default="Go to https://gitlab.com/macaroon777sweet/test/-/work_items/8. Comment on the given issue saying we are working on it.")
    parser.add_argument("--model", default="o1", help="Model name — OpenAI (e.g. o1, gpt-4o) or Anthropic (e.g. claude-sonnet-4-6) (default: o1)")
    parser.add_argument("--max-steps", type=int, default=20, help="Max agent steps (default: 20)")
    args = parser.parse_args()

    asyncio.run(main(task=args.task, model=args.model, max_steps=args.max_steps))
