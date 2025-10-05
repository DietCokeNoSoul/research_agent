from agent.graph import Agent

if __name__ == "__main__":
    question = "我想找一篇文章，我记得是介绍multi-scale neighbor topology技术的，然后对Transformer模型进行了改进"
    agent = Agent()
    agent.agent(question)
    # response = agent.agent(question)
    # print("Final Response:", response)