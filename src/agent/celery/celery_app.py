from celery import Celery

app = Celery(
    'memory_tasks', # 任务模块名
    broker='amqp://guest:guest@localhost:5672//'  # RabbitMQ 默认地址
)

# 配置Celery使用指定的交换机和队列
app.conf.update(
    # 任务序列化设置
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # 使用你指定的交换机和队列配置
    task_default_queue='memory.queue',           # 默认队列名
    task_default_exchange='memory.direct',       # 默认交换机名
    task_default_exchange_type='direct',         # 交换机类型
    task_default_routing_key='memory.info',      # 默认路由键
    
    # 任务路由配置 - 强制所有任务使用指定的队列
    task_routes={
        'agent.celery.tasks.send_memory_message': {
            'queue': 'memory.queue',
            'exchange': 'memory.direct',
            'routing_key': 'memory.info',
        },
        # 可以添加更多任务的路由配置
        '*': {  # 通配符，所有其他任务也使用相同配置
            'queue': 'memory.queue',
            'exchange': 'memory.direct', 
            'routing_key': 'memory.info',
        }
    },
    
    # 队列定义 - 明确定义队列和绑定关系
    task_queues={
        'memory.queue': {
            'exchange': 'memory.direct',
            'exchange_type': 'direct',
            'routing_key': 'memory.info',
            'durable': True,
        }
    },
    
    # 禁用默认队列和交换机的创建
    task_create_missing_queues=False,  # 不自动创建缺失的队列
)