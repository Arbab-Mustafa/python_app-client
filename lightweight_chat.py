"""
Lightweight Chat Implementation
Replaces LangChain conversation chain with minimal dependencies
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from lightweight_vectorstore import LightweightVectorStore

logger = logging.getLogger(__name__)

class LightweightConversationChain:
    """Lightweight conversation chain without LangChain dependencies"""
    
    def __init__(self, llm, vectorstore: LightweightVectorStore, memory=None, prompt_template=None):
        """
        Initialize conversation chain
        
        Args:
            llm: OpenAI client
            vectorstore: Vector store for retrieval
            memory: Conversation memory (optional)
            prompt_template: Custom prompt template
        """
        self.llm = llm
        self.vectorstore = vectorstore
        self.memory = memory or LightweightMemory()
        self.prompt_template = prompt_template or self._default_prompt_template()
    
    def _default_prompt_template(self):
        """Default prompt template"""
        return """You are a licensed school psychologist supervisor and a licensed psychologist with expertise in Texas state law and school psychology practices. Your goal is to provide accurate, context-based answers with clear citations and structured reasoning.

Use only the information provided in the Context below. If you cannot answer based on the provided context, respond with: 'I don't know based on the information provided.'

Context: {context}
Chat History: {chat_history}
Question: {question}

Answer:"""
    
    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process a conversation turn"""
        try:
            question = inputs.get('question', '')
            
            # Get relevant documents
            retriever = self.vectorstore.as_retriever(search_kwargs={
                'k': 30,
                'score_threshold': 0.42
            })
            
            docs = retriever.get_relevant_documents(question)
            context = "\n\n".join([doc['page_content'] for doc in docs])
            
            # Get chat history
            chat_history = self.memory.get_chat_history()
            
            # Format prompt
            prompt = self.prompt_template.format(
                context=context,
                chat_history=chat_history,
                question=question
            )
            
            # Generate response using the configured model
            answer = self.llm(prompt)
            
            # Update memory
            self.memory.add_user_message(question)
            self.memory.add_ai_message(answer)
            
            return {
                'question': question,
                'answer': answer,
                'chat_history': self.memory.get_messages(),
                'source_documents': docs
            }
            
        except Exception as e:
            logger.error(f"Error in conversation chain: {e}")
            return {
                'question': inputs.get('question', ''),
                'answer': 'An error occurred while processing your question. Please try again.',
                'chat_history': self.memory.get_messages(),
                'source_documents': []
            }


class LightweightMemory:
    """Simple conversation memory"""
    
    def __init__(self):
        self.messages = []
    
    def add_user_message(self, message: str):
        """Add user message to memory"""
        self.messages.append({"role": "user", "content": message})
    
    def add_ai_message(self, message: str):
        """Add AI message to memory"""
        self.messages.append({"role": "assistant", "content": message})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages"""
        return self.messages
    
    def get_chat_history(self) -> str:
        """Get chat history as formatted string"""
        history = []
        for msg in self.messages[-10:]:  # Last 10 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            history.append(f"{role}: {msg['content']}")
        return "\n".join(history)
    
    def clear(self):
        """Clear memory"""
        self.messages = []


class LightweightLLM:
    """Lightweight LLM wrapper"""
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0):
        """
        Initialize LLM
        
        Args:
            model: OpenAI model name
            temperature: Generation temperature
        """
        self.model = model
        self.temperature = temperature
        self.client = None  # Initialize client only when needed
    
    def _get_client(self):
        """Get OpenAI client, initializing if needed"""
        if self.client is None:
            self.client = OpenAI()
        return self.client
    
    def __call__(self, prompt: str) -> str:
        """Generate response"""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in LLM call: {e}")
            return "An error occurred while generating the response."


# Factory functions for compatibility
def ConversationalRetrievalChain_from_llm(llm, vectorstore, memory=None, **kwargs):
    """Factory function for creating conversation chain"""
    return LightweightConversationChain(llm, vectorstore, memory)


def ConversationBufferMemory(memory_key='chat_history', output_key='answer', return_messages=True):
    """Factory function for creating memory"""
    return LightweightMemory()


class NoOpLLMChain:
    """No-op LLM chain for compatibility"""
    
    def __init__(self, llm):
        self.llm = llm
    
    def run(self, question: str, *args, **kwargs) -> str:
        return question 