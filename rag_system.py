# rag_system.py

import logging
import fitz
import docx
from sentence_transformers import SentenceTransformer
import chromadb
from typing import List, Dict, Set
from config import Config
from openai import OpenAI
import os
import db_manager # Import the database manager

logger = logging.getLogger(__name__)

# --- Global Variables & Initialization ---
embedding_model = None
chroma_client = None
collection = None
openai_client = None

FALLBACK_RESPONSE = "I'm not sure how to answer that. Can you please rephrase your question?"
ERROR_RESPONSE = "I seem to be having a technical issue. Please try asking again in a moment."


def initialize_rag_system():
    global embedding_model, chroma_client, collection, openai_client
    
    if embedding_model: return

    logger.info("Initializing Sentence Transformer model...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    logger.info(f"Initializing ChromaDB client at: {db_path}")
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="zoom_meeting_docs", metadata={"hnsw:space": "cosine"})
    
    logger.info("Initializing OpenAI client...")
    openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

    # Initialize the database connection pool
    db_manager.initialize_db_pool()
    
    logger.info("✅ RAG System Initialized.")

# DocumentProcessor class remains unchanged
class DocumentProcessor:
    @staticmethod
    def extract_text(file_path: str, filename: str) -> str:
        if filename.lower().endswith('.pdf'):
            with fitz.open(file_path) as doc:
                return "".join(page.get_text() for page in doc)
        elif filename.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif filename.lower().endswith('.docx'):
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs)
        else:
            raise ValueError(f"Unsupported file type: {filename}")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 250, overlap: int = 50) -> List[str]:
        words = text.split()
        if not words: return []
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunks.append(' '.join(words[i:i + chunk_size]))
        return chunks

class RAGSystem:
    # add_document_chunk and add_document methods remain unchanged
    def add_document_chunk(self, document_text: str, source_id: str, metadata: dict):
        try:
            embedding = embedding_model.encode([document_text], show_progress_bar=False)
            chunk_id = f"{source_id}_{hash(document_text)}"
            collection.add(embeddings=embedding.tolist(), documents=[document_text], ids=[chunk_id], metadatas=[metadata])
            return True
        except Exception as e:
            logger.error(f"Error adding single chunk from '{source_id}': {e}")
            return False

    def add_document(self, source_id: str, file_path: str, filename: str):
        try:
            text = DocumentProcessor.extract_text(file_path, filename)
            if not text.strip(): return False
            chunks = DocumentProcessor.chunk_text(text)
            embeddings = embedding_model.encode(chunks, show_progress_bar=False)
            chunk_ids = [f"{source_id}_{filename}_{i}" for i in range(len(chunks))]
            collection.add(embeddings=embeddings.tolist(), documents=chunks, ids=chunk_ids, metadatas=[{"source_document": filename, "type": "generic"} for _ in chunks])
            return True
        except Exception as e:
            logger.error(f"Error adding document '{filename}': {e}")
            return False

    def _find_best_command_match(self, question: str, commands: List[Dict]) -> Dict:
        """Finds the best command match based on keyword scoring."""
        lower_question_words = set(question.lower().strip().split())
        stop_words = {'a', 'an', 'the', 'to', 'for', 'is', 'on', 'everyone', 'please', 'can', 'you', 'could'}
        
        best_match = None
        highest_score = 0

        for command in commands:
            # Create a comprehensive set of keywords for this command
            command_keywords = set()
            for trigger in command['triggers']:
                words = trigger.strip().lower().split()
                significant_words = {word for word in words if word not in stop_words}
                command_keywords.update(significant_words)

            # Score by counting the number of matching keywords
            common_words = lower_question_words.intersection(command_keywords)
            score = len(common_words)

            if score > highest_score:
                highest_score = score
                best_match = command
        
        # A match is only valid if it scores above a certain threshold.
        # This prevents matching on single, common words like "send" or "link".
        # We require at least 2 significant keywords to match.
        if best_match and highest_score >= 2:
            logger.info(f"Best command match is '{best_match['name']}' with a score of {highest_score}.")
            return best_match
        
        return None


    def generate_response(self, question: str, is_privileged_user: bool = False) -> Dict:
        """
        Generates a response using a flexible keyword-matching system for host commands,
        and falls back to a RAG search for all other queries.
        """
        logger.info(f"Processing message: '{question}' (Privileged: {is_privileged_user})")
        
        try:
            # --- TRACK 1: FLEXIBLE HOST COMMAND CHECK FROM DATABASE ---
            if is_privileged_user:
                host_commands = db_manager.get_host_commands() # Fetch live commands from DB
                matched_command = self._find_best_command_match(question, host_commands)

                if matched_command:
                    logger.info(f"✅ Executing matched host command '{matched_command['name']}'.")
                    return {
                        "action": "broadcast",
                        "bot_classification": f"Command: {matched_command['name']}",
                        "broadcast_message": matched_command['broadcast_message'],
                        "ack_message": matched_command['ack_message']
                    }
            
            # --- TRACK 2: SEMANTIC RAG SEARCH FOR Q&A and RULES ---
            logger.info("-> No host command matched. Proceeding with semantic RAG search.")
            query_embedding = embedding_model.encode([question], show_progress_bar=False)
            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=5,
                include=["documents"]
            )
            context_docs = results.get('documents', [[]])[0]

            if not context_docs:
                logger.warning(f"Vector search returned no documents for: '{question}'. Using fallback.")
                return {"reply": FALLBACK_RESPONSE, "bot_classification": "Fallback"}

            context_str = "\n\n---\n\n".join(context_docs)
            
            system_prompt = (
                "You are an expert AI assistant for 'The Fitness Doctor'. Your persona is friendly, professional, and helpful. "
                # ... (rest of prompt)
            )
            user_prompt = f"CONTEXT:\n{context_str}\n\nUSER QUESTION: {question}\n\nAnswer:"

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=250, temperature=0.4
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"LLM generated answer: '{answer}'")
            return {"reply": answer, "bot_classification": "RAG"}

        except Exception as e:
            logger.error(f"An unexpected error occurred in generate_response: {e}", exc_info=True)
            return {"reply": ERROR_RESPONSE, "bot_classification": "Error"}

def is_a_meaningful_message(message: str) -> bool:
    return len(message.strip()) > 2 or message.strip().lower() == 'stop'