from run_agent import AIAgent

agent = AIAgent(
    model="gpt-5.5",
    quiet_mode=True,
)
response = agent.chat("去远程主机 bianbu@10.0.90.61 查看cpu信息")
print(response)