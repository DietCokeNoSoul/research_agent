from agent.celery.celery_app import app
from agent.celery.queue_client import MemoryQueueClient
from loguru import logger


@app.task  # 任务装饰器，定义一个异步任务
def send_memory_message(data: dict):
    """
    发送内存消息到RabbitMQ队列
    使用连接池实现连接复用，提高性能
    """
    logger.info(f"开始发送内存消息: {data.get('text', '')[:50]}...")
    
    try:
        # 使用连接池的客户端，不需要手动关闭连接
        mq = MemoryQueueClient(routing_key='memory.info')
        mq.send(data)
        
        logger.info("内存消息发送成功")
        return {"status": "success", "message": "消息已发送到memory.queue队列"}
        
    except Exception as e:
        logger.error(f"发送内存消息失败: {e}")
        return {"status": "error", "message": str(e)}