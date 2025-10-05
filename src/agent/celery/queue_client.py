import pika
import json
import threading
import atexit
import weakref
from loguru import logger
from typing import Optional

class RabbitMQConnectionPool:
    """RabbitMQ连接池单例类，管理连接复用"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self.connection: Optional[pika.BlockingConnection] = None
            self.channel: Optional[pika.channel.Channel] = None
            self.host = 'localhost'
            self._setup_lock = threading.Lock()
            self._initialized = True
            
            # 注册程序退出时的清理函数
            atexit.register(self._cleanup_on_exit)
            logger.info("RabbitMQ连接池初始化完成，已注册退出清理")
    
    def _cleanup_on_exit(self):
        """程序退出时自动清理资源"""
        try:
            self.close()
            logger.info("程序退出，RabbitMQ连接池资源已清理")
        except Exception as e:
            logger.error(f"程序退出时清理RabbitMQ连接失败: {e}")
    
    def get_connection_and_channel(self):
        """获取连接和channel，如果不存在则创建"""
        with self._setup_lock:
            if self.connection is None or self.connection.is_closed:
                self._create_connection()
            
            if self.channel is None or self.channel.is_closed:
                self._create_channel()
                
            return self.connection, self.channel
    
    def _create_connection(self):
        """创建新的RabbitMQ连接"""
        try:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host)
            )
            logger.info(f"创建新的RabbitMQ连接到 {self.host}")
        except Exception as e:
            logger.error(f"创建 RabbitMQ 连接失败: {e}")
            raise
    
    def _create_channel(self):
        """创建新的channel"""
        try:
            self.channel = self.connection.channel()
            # 设置基本的交换机和队列配置
            self._setup_exchange_and_queue()
            logger.info("创建新的RabbitMQ channel")
        except Exception as e:
            logger.error(f"创建 RabbitMQ channel 失败: {e}")
            raise
    
    def _setup_exchange_and_queue(self):
        """设置交换机和队列（只在创建新channel时执行一次）"""
        # 声明交换机
        self.channel.exchange_declare(
            exchange='memory.direct', 
            exchange_type='direct', 
            durable=True
        )
        
        # 声明队列
        self.channel.queue_declare(queue='memory.queue', durable=True)
        
        # 绑定队列到交换机
        self.channel.queue_bind(
            exchange='memory.direct',
            queue='memory.queue',
            routing_key='memory.info'
        )
        logger.info("交换机和队列设置完成")
    
    def close(self):
        """关闭连接池中的所有连接"""
        with self._setup_lock:
            if self.channel and not self.channel.is_closed:
                try:
                    self.channel.close()
                    logger.info("RabbitMQ channel 已关闭")
                except Exception as e:
                    logger.warning(f"关闭RabbitMQ channel时出现异常: {e}")
            
            if self.connection and not self.connection.is_closed:
                try:
                    self.connection.close()
                    logger.info("RabbitMQ 连接已关闭")
                except Exception as e:
                    logger.warning(f"关闭RabbitMQ连接时出现异常: {e}")
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试或特殊情况）"""
        with cls._lock:
            if cls._instance:
                cls._instance.close()
                cls._instance = None
                logger.info("RabbitMQ连接池单例已重置")


class MemoryQueueClient:
    """内存队列客户端，使用连接池实现连接复用"""
    
    def __init__(self, routing_key='memory.info'):
        self.routing_key = routing_key
        self.pool = RabbitMQConnectionPool()  # 连接池实例
        logger.info(f"MemoryQueueClient 初始化，使用路由键: {routing_key}")
    
    def send(self, data: dict):
        """发送消息到指定队列"""
        try:
            # 从连接池获取连接和channel
            connection, channel = self.pool.get_connection_and_channel()
            
            message = json.dumps(data)
            channel.basic_publish(
                exchange='memory.direct',
                routing_key=self.routing_key,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            logger.info(
                f"消息已发送到队列 'memory.queue' "
                f"(交换机: memory.direct, 路由键: {self.routing_key})"
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            # 如果发送失败，尝试重置连接
            self.pool.connection = None
            self.pool.channel = None
            raise