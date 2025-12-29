On this page
  * [ Create an agent](https://docs.langchain.com/oss/python/langchain/overview#create-an-agent)
  * [ Core benefits](https://docs.langchain.com/oss/python/langchain/overview#core-benefits)


# LangChain overview
Copy page
LangChain is an open source framework with a pre-built agent architecture and integrations for any model or tool — so you can build agents that adapt as fast as the ecosystem evolves
Copy page
LangChain is the easiest way to start building agents and applications powered by LLMs. With under 10 lines of code, you can connect to OpenAI, Anthropic, Google, and [more](https://docs.langchain.com/oss/python/integrations/providers/overview). LangChain provides a pre-built agent architecture and model integrations to help you get started quickly and seamlessly incorporate LLMs into your agents and applications. We recommend you use LangChain if you want to quickly build agents and autonomous applications. Use [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview), our low-level agent orchestration framework and runtime, when you have more advanced needs that require a combination of deterministic and agentic workflows, heavy customization, and carefully controlled latency. LangChain [agents](https://docs.langchain.com/oss/python/langchain/agents) are built on top of LangGraph in order to provide durable execution, streaming, human-in-the-loop, persistence, and more. You do not need to know LangGraph for basic LangChain agent usage.
```
# pip install -qU langchain "langchain[anthropic]"
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)

```

See the [Installation instructions](https://docs.langchain.com/oss/python/langchain/install) and [Quickstart guide](https://docs.langchain.com/oss/python/langchain/quickstart) to get started building your own agents and applications with LangChain.
## [Standard model interface Different providers have unique APIs for interacting with models, including the format of responses. LangChain standardizes how you interact with models so that you can seamlessly swap providers and avoid lock-in. Learn more ](https://docs.langchain.com/oss/python/langchain/models)## [Easy to use, highly flexible agent LangChain’s agent abstraction is designed to be easy to get started with, letting you build a simple agent in under 10 lines of code. But it also provides enough flexibility to allow you to do all the context engineering your heart desires. Learn more ](https://docs.langchain.com/oss/python/langchain/agents)## [Built on top of LangGraph LangChain’s agents are built on top of LangGraph. This allows us to take advantage of LangGraph’s durable execution, human-in-the-loop support, persistence, and more. Learn more ](https://docs.langchain.com/oss/python/langgraph/overview)## [Debug with LangSmith Gain deep visibility into complex agent behavior with visualization tools that trace execution paths, capture state transitions, and provide detailed runtime metrics. Learn more ](https://docs.langchain.com/langsmith/home)
* * *
[Edit this page on GitHub](https://github.com/langchain-ai/docs/edit/main/src/oss/langchain/overview.mdx) or [file an issue](https://github.com/langchain-ai/docs/issues/new/choose).
[Connect these docs](https://docs.langchain.com/use-these-docs) to Claude, VSCode, and more via MCP for real-time answers.
Was this page helpful?
YesNo
[ Install LangChain Next ](https://docs.langchain.com/oss/python/langchain/install)
[![light logo](https://mintcdn.com/langchain-5e9cc07a/Xbr8HuVd9jPi6qTU/images/brand/langchain-docs-teal.svg?fit=max&auto=format&n=Xbr8HuVd9jPi6qTU&q=85&s=16111530672bf976cb54ef2143478342)![dark logo](https://mintcdn.com/langchain-5e9cc07a/Xbr8HuVd9jPi6qTU/images/brand/langchain-docs-lilac.svg?fit=max&auto=format&n=Xbr8HuVd9jPi6qTU&q=85&s=b70fb1a2208670492ef94aef14b680be)](https://docs.langchain.com/)
[](https://github.com/langchain-ai)[](https://x.com/LangChainAI)[](https://www.linkedin.com/company/langchain/)[](https://www.youtube.com/@LangChain)
Resources
[Forum](https://forum.langchain.com/)[Changelog](https://changelog.langchain.com/)[LangChain Academy](https://academy.langchain.com/)[Trust Center](https://trust.langchain.com/)
Company
[About](https://langchain.com/about)[Careers](https://langchain.com/careers)[Blog](https://blog.langchain.com/)
[](https://github.com/langchain-ai)[](https://x.com/LangChainAI)[](https://www.linkedin.com/company/langchain/)[](https://www.youtube.com/@LangChain)
[Powered by](https://www.mintlify.com?utm_campaign=poweredBy&utm_medium=referral&utm_source=langchain-5e9cc07a)
Assistant
Responses are generated using AI and may contain mistakes.
