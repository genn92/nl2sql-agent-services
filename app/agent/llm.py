"""Agent 的 LLM 客户端定义

基于 LangChain 初始化聊天模型实例，供代理图各节点共享调用。
通过 OpenAI 兼容协议接入（当前指向硅基流动端点），模型名称、
API 密钥、服务地址均来自 config/app_config.yaml（密钥经 .env
环境变量 LLM_API_KEY 注入），不在此处硬编码。
"""

from langchain.chat_models import init_chat_model

from app.config.app_config import app_config

# 全局唯一的模型客户端；init_chat_model 按 model_provider 自动分派到
# 对应的集成实现，import 本模块即完成初始化，各节点直接复用
llm = init_chat_model(
    model=app_config.llm.model_name,  # 模型名称，如 Pro/zai-org/GLM-5.1
    model_provider="openai",  # 使用 OpenAI 兼容协议（服务端为硅基流动，非 OpenAI 官方）
    api_key=app_config.llm.api_key,  # 来自 .env 的 LLM_API_KEY
    base_url=app_config.llm.base_url,  # OpenAI 兼容端点地址
    temperature=0,  # 确定性输出：NL2SQL 生成 SQL 需要稳定可复现，压低随机性
)

if __name__ == "__main__":
    # 冒烟测试入口：直接运行本模块（uv run python -m app.agent.llm）
    # 可验证配置加载与模型连通性
    content = llm.invoke("介绍下你自己").content
    print(content)
