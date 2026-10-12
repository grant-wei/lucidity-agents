"""One tiny model call to prove the key, the .env lookup and the usage log all work."""
from pydantic_ai import Agent

from lucidity import config
from lucidity.llm import run_agent

if __name__ == "__main__":
    print("env file:", config.ENV_PATH)
    print("model:", config.MODEL)
    out, row = run_agent(Agent(instructions="Reply with one word."), "Say ready.", name="smoke")
    print("reply:", out)
    print("usage:", row)
