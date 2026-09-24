"""
Setup:
1. Get your API key from https://cloud.browser-use.com/new-api-key
2. Set environment variable: export BROWSER_USE_API_KEY="your-key"
"""

from dotenv import load_dotenv

from browser_use import Agent, ChatAnthropic, ChatOpenAI, Browser

load_dotenv()

llm = ChatOpenAI(
    model='gpt-4o-mini',
)

browser = Browser(
    headless=False,
    cdp_url="http://localhost:9222",
    minimum_wait_page_load_time=2.0,
    wait_for_network_idle_page_load_time=2.0,
    wait_between_actions=2.0,
)

agent = Agent(
	task='Comment on the given issue saying we are working on it.',
	llm=llm,
    browser=browser,
    initial_actions=[{"navigate": {"url": "http://16.58.0.143:8023/byteblaze/dotfiles/-/issues/2", "new_tab": True}}],
)
agent.run_sync()
