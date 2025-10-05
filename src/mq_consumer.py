import pika
import json
from loguru import logger
from agent.memory_manager import Memory_Manager  # 假设你的 Memory_Manager 类在 memory_manager.py

def memory_queue_consumer():
    # 创建 Memory_Manager 实例
    memory_manager = Memory_Manager()

    # RabbitMQ连接参数
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    
    # 声明交换机（确保交换机存在）
    channel.exchange_declare(exchange='memory.direct', exchange_type='direct', durable=True)
    
    # 监听的队列名：memory.queue
    queue_name = 'memory.queue'
    
    # 声明队列（确保队列存在）
    channel.queue_declare(queue=queue_name, durable=True)
    
    # 绑定队列到交换机：通过路由键mory.info将队列memory.queue绑定到交换机memory.direct
    channel.queue_bind(exchange='memory.direct', queue=queue_name, routing_key='memory.info')

    # 消费回调
    def callback(ch, method, properties, body):
        logger.info(f"Received message")
        try:
            # 解析消息体
            message = json.loads(body)
            question = message[0][0]["text"]
            type = message[0][0]["type"]
            if question:
                memory_manager.task_routing(question, type)  # 处理消息
            else:
                logger.warning("No 'text' field in message, skipping.")
            # 手动ack，保证消息处理完才删除
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # 可以选择nack并requeue，或丢弃，nack表示消息处理失败，requeue=False表示不重新入队
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    # 启动消费者（默认推送模式 - Push Model）
    # auto_ack=False表示需要手动确认消息处理完成
    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,  # 消息回调函数 - RabbitMQ推送消息时自动调用
        auto_ack=False  # 手动ACK模式，确保消息处理完成后才从队列删除
    )

    logger.info(f"Waiting for messages in queue: {queue_name}")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    finally:
        connection.close()
        
        
if __name__ == "__main__":
    memory_queue_consumer()
