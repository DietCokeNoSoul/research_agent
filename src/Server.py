from agent.graph import Agent

if __name__ == "__main__":
    question = "我想找一篇文章，有关Transformer的图形优化方式的，然后我记得是2020年发表的"
    agent = Agent()
    agent.agent(question)
    # response = agent.agent(question)
    # print("Final Response:", response)