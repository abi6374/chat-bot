from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory


chat_history = ChatMessageHistory()
memory = ConversationBufferMemory(chat_memory=chat_history, return_messages=True)

