import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from lightweight_vectorstore import LightweightVectorStore, from_texts
from lightweight_chat import (
    LightweightConversationChain, 
    LightweightMemory, 
    LightweightLLM,
    ConversationalRetrievalChain_from_llm,
    ConversationBufferMemory,
    NoOpLLMChain
)
from lightweight_text_splitter import CharacterTextSplitter
from htmlTempletes import css, bot_template, user_template
from prompts import professional_prompt
import os
import pickle
import logging
from datetime import datetime
import json
from config import config

# Import GCS storage if enabled
gcs_storage = None
if config.GCS_USE_STORAGE:
    try:
        from gcs_storage import GCSStorage
        gcs_storage = GCSStorage()
        logger = logging.getLogger(__name__)
        logger.info("GCS Storage enabled for embeddings")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"GCS Storage initialization failed: {e}. Falling back to local storage.")
        gcs_storage = None
else:
    logger = logging.getLogger(__name__)
    logger.info("Using local storage for embeddings")

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for production
EMBEDDINGS_PATH = "static_embeddings/faiss_index"
CHUNKS_PATH = "static_embeddings/text_chunks.pkl"
METADATA_PATH = "static_embeddings/metadata.json"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change in production

def load_static_embeddings():
    """Load pre-processed embeddings and chunks"""
    try:
        # Try GCS storage first if enabled
        if gcs_storage and config.GCS_USE_STORAGE:
            logger.info("Attempting to load embeddings from Google Cloud Storage...")
            vectorstore, text_chunks, metadata = gcs_storage.load_embeddings()
            if vectorstore is not None:
                logger.info(f"✅ Loaded embeddings from GCS: {len(text_chunks)} chunks")
                return vectorstore, text_chunks, metadata
            else:
                logger.warning("GCS embeddings not found, trying local storage...")
        
        # Fallback to local storage
        if os.path.exists(EMBEDDINGS_PATH) and os.path.exists(CHUNKS_PATH):
            # Load lightweight vectorstore
            try:
                vectorstore = LightweightVectorStore.load_local(EMBEDDINGS_PATH)
            except Exception as e:
                logger.error(f"Error loading vectorstore: {e}")
                return None, None, None

            # Load chunks with proper error handling
            try:
                with open(CHUNKS_PATH, 'rb') as f:
                    # Try with allow_dangerous_deserialization first, fallback to regular load
                    try:
                        text_chunks = pickle.load(f, allow_dangerous_deserialization=True)
                    except TypeError:
                        # Fallback for older pickle versions
                        f.seek(0)  # Reset file pointer
                        text_chunks = pickle.load(f)
            except Exception as e:
                logger.error(f"Error loading chunks: {e}")
                return None, None, None

            # Load metadata
            metadata = {}
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH, 'r') as f:
                    metadata = json.load(f)

            logger.info(f"✅ Loaded embeddings from local storage: {len(text_chunks)} chunks")
            return vectorstore, text_chunks, metadata
        else:
            logger.info("No embeddings found. This is normal for first-time setup.")
            return None, None, None
    except Exception as e:
        logger.warning(f"Error loading static embeddings: {e}")
        logger.info("This is normal for first-time setup. Upload PDFs to create embeddings.")
        return None, None, None

def get_pdf_text(pdf_docs):
    """Extract text from PDF documents"""
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text()
        except Exception as e:
            logger.error(f"Error processing PDF {pdf.name}: {e}")
    return text

def get_text_chunks(text):
    """Split text into chunks for processing"""
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_text(text)
    return chunks

def create_static_embeddings(pdf_docs):
    """Create and save static embeddings for production use"""
    try:
        # Create embeddings directory for local storage
        os.makedirs("static_embeddings", exist_ok=True)
        
        # Process PDFs
        raw_text = get_pdf_text(pdf_docs)
        if not raw_text.strip():
            raise ValueError("No text extracted from PDFs")
        
        # Create chunks
        text_chunks = get_text_chunks(raw_text)
        
        # Create lightweight vectorstore
        vectorstore = from_texts(texts=text_chunks)
        vectorstore.fit()
        
        # Save to local storage (always as backup)
        vectorstore.save_local(EMBEDDINGS_PATH)
        
        # Save chunks locally
        with open(CHUNKS_PATH, 'wb') as f:
            pickle.dump(text_chunks, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Save metadata locally
        metadata = {
            "created_at": datetime.now().isoformat(),
            "num_chunks": len(text_chunks),
            "num_pdfs": len(pdf_docs),
            "pdf_names": [pdf.name for pdf in pdf_docs],
            "storage_type": "local_and_gcs" if gcs_storage and config.GCS_USE_STORAGE else "local_only"
        }
        with open(METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save to GCS if enabled
        if gcs_storage and config.GCS_USE_STORAGE:
            logger.info("Saving embeddings to Google Cloud Storage...")
            gcs_success = gcs_storage.save_embeddings(vectorstore, text_chunks, metadata)
            if gcs_success:
                logger.info("✅ Embeddings saved to both local storage and GCS")
            else:
                logger.warning("⚠️ Failed to save to GCS, but local storage is available")
        else:
            logger.info("✅ Embeddings saved to local storage only")
        
        logger.info(f"Static embeddings created successfully: {len(text_chunks)} chunks")
        return True
    except Exception as e:
        logger.error(f"Error creating static embeddings: {e}")
        return False

def get_conversation_chain(vectorstore, model_name):
    """Create conversation chain with selected model"""
    try:
        # Create LLM based on selection
        if model_name == 'GPT-3.5-turbo':
            llm = LightweightLLM(model="gpt-3.5-turbo", temperature=0)
        elif model_name == 'GPT-4':
            llm = LightweightLLM(model="gpt-4", temperature=0)
        elif model_name == 'GPT-4o':
            llm = LightweightLLM(model="gpt-4o", temperature=0)
        elif model_name == 'GPT-4o-mini':
            llm = LightweightLLM(model="gpt-4o-mini", temperature=0)
        else:
            st.error('Invalid model selection', icon="🚨")
            return None
        
        # Create memory
        memory = ConversationBufferMemory(
            memory_key='chat_history', 
            output_key='answer', 
            return_messages=True
        )
        
        # Create conversation chain with professional prompt
        prompt_template = professional_prompt()
        conv_rqa = LightweightConversationChain(
            llm=llm,
            vectorstore=vectorstore,
            memory=memory,
            prompt_template=prompt_template
        )
        
        return conv_rqa
    except Exception as e:
        logger.error(f"Error creating conversation chain: {e}")
        return None

def select_model():
    """Model selection for production"""
    model = st.selectbox(
        'Select the AI model',
        ('GPT-4o-mini', 'GPT-4o', 'GPT-4', 'GPT-3.5-turbo')
    )
    return model

def handle_userinput(user_question):
    """Handle user input and generate response"""
    try:
        if not user_question.strip():
            st.warning("Please enter a question.")
            return
            
        if st.session_state.conversation is None:
            st.error("System not initialized. Please refresh the page.")
            return
        
        with st.spinner("Processing your question..."):
            response = st.session_state.conversation({'question': user_question})
            
        if response and 'answer' in response:
            st.session_state.chat_history = response['chat_history']
            
            # Display conversation
            for i, message in enumerate(st.session_state.chat_history):
                if i % 2 == 0:
                    st.write(user_template.replace("{{MSG}}", message['content']), unsafe_allow_html=True)
                else:
                    st.write(bot_template.replace("{{MSG}}", message['content']), unsafe_allow_html=True)
        else:
            st.error("Failed to get response from AI.")
            
    except Exception as e:
        logger.error(f"Error handling user input: {e}")
        st.error("An error occurred while processing your question. Please try again.")

def admin_interface():
    """Admin interface for managing PDFs and embeddings"""
    st.subheader("🔧 Admin Panel")
    
    # Password protection
    password = st.text_input("Admin Password", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("Incorrect password")
        return
    
    st.success("Admin access granted")
    
    # PDF upload for admin
    st.subheader("Upload PDFs (Admin Only)")
    pdf_docs = st.file_uploader(
        "Upload PDFs to update knowledge base", 
        accept_multiple_files=True,
        type=['pdf']
    )
    
    if st.button("Update Knowledge Base"):
        if pdf_docs:
            with st.spinner("Processing PDFs and updating embeddings..."):
                success = create_static_embeddings(pdf_docs)
                if success:
                    st.success("Knowledge base updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update knowledge base")
        else:
            st.warning("Please upload at least one PDF")
    
    # Show current metadata
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, 'r') as f:
            metadata = json.load(f)
        st.subheader("Current Knowledge Base Info")
        st.json(metadata)

def main():
    """Main application function"""
    load_dotenv()
    
    # Page configuration
    st.set_page_config(
        page_title="Texas School Psychology Assistant",
        page_icon="🎓",
        layout="wide"
    )
    
    # Apply CSS
    st.write(css, unsafe_allow_html=True)
    
    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    
    # Main header
    st.header("🎓 Texas School Psychology Assistant")
    st.markdown("Professional guidance for Texas school psychology practices")
    
    # Load static embeddings
    vectorstore, text_chunks, metadata = load_static_embeddings()
    
    if vectorstore is None:
        # Sidebar (Left side) - even for first-time setup
        with st.sidebar:
            st.subheader("⚙️ Settings")
            st.warning("📚 **Knowledge Base Not Found**")
            st.info("""
            This is normal for first-time setup. To get started:
            
            1. **Upload PDFs** using the admin interface below
            2. **Click "Update Knowledge Base"** to process your documents
            3. **Start asking questions** once the knowledge base is created
            """)
            
            # Admin interface for first-time setup
            st.subheader("🔧 **First-Time Setup**")
            admin_interface()
        
        # Main area (Right side) - show setup instructions
        st.subheader("🎓 Welcome to Texas School Psychology Assistant")
        st.markdown("Professional guidance for Texas school psychology practices")
        
        st.info("""
        **Getting Started:**
        
        The knowledge base needs to be initialized with your documents. 
        Please use the admin interface in the sidebar (left) to:
        
        1. **Upload your PDF documents** (guidelines, laws, procedures)
        2. **Click "Update Knowledge Base"** to process them
        3. **Start asking questions** once processing is complete
        
        This is a one-time setup process. Once completed, you'll be able to ask questions about Texas school psychology practices.
        """)
        
        st.stop()
    
    # Initialize conversation if not already done
    if st.session_state.conversation is None:
        with st.spinner("Initializing AI assistant..."):
            model = 'GPT-4o-mini'  # Default model
            st.session_state.conversation = get_conversation_chain(vectorstore, model)
    
    # Sidebar (Left side)
    with st.sidebar:
        st.subheader("⚙️ Settings")
        
        # Model selection
        model = select_model()
        if st.button("Update Model"):
            with st.spinner("Updating model..."):
                st.session_state.conversation = get_conversation_chain(vectorstore, model)
                st.success(f"Model updated to {model}")
        
        # Knowledge base info
        if metadata:
            st.subheader("📚 Knowledge Base")
            st.write(f"**Documents:** {metadata.get('num_pdfs', 0)}")
            st.write(f"**Chunks:** {metadata.get('num_chunks', 0)}")
            st.write(f"**Updated:** {metadata.get('created_at', 'Unknown')[:10]}")
        
        # Admin access
        if st.checkbox("Admin Access"):
            admin_interface()
    
    # Main chat interface (Right side)
    st.subheader("💬 Ask Your Question")
    user_question = st.text_input(
        "Ask about Texas school psychology practices, laws, or procedures:",
        placeholder="e.g., What are the requirements for ARD committee meetings?"
    )
    
    if user_question:
        handle_userinput(user_question)
    
    # Clear chat button
    if st.button("Clear Chat History"):
        st.session_state.chat_history.clear()
        st.rerun()

if __name__ == '__main__':
    main()