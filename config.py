import logging
import os

from langchain_openai import ChatOpenAI

# 数据库文件路径，使用相对路径，位于根目录下
DB_PATH = os.path.join('E:\\AI_PJDataBase', 'process_db.db')

# 配置日志记录
def setup_logging(log_level=logging.INFO, logger_name='scp'):
    # 创建或获取logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if not logger.handlers:
        # 创建处理器
        stream_handler = logging.StreamHandler()
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        
        # 添加处理器到logger
        logger.addHandler(stream_handler)
    
    return logger

# 创建LLM客户端
def create_llm_client():
    # 获取logger
    logger = logging.getLogger('scp')
    
    try:
        # 使用langchain的ChatOpenAI客户端
        llm_client = ChatOpenAI(
            model="deepseek-chat",
            api_key="sk-4IkjoPYhHMMjDajyXc51YkBbYKeYncbxF4FdXJRg8IBv6lkU",
            base_url="https://api.agicto.cn/v1"
        )
        logger.info("LLM客户端初始化成功")
        return llm_client
    except Exception as e:
        logger.error(f"初始化LLM客户端失败: {str(e)}")
        raise
