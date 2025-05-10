import os
from langchain_openai.chat_models import ChatOpenAI
from utils.env_variables import OPENAI_API_KEY

llm = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    model_name='gpt-4o'
)