# ingest.py

import os
import logging
import traceback
import re
import shutil
from rag_system import RAGSystem, initialize_rag_system
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = "knowledge_base"

def ingest_knowledge_base():
    """
    Scans the knowledge base directory, processing documents for the RAG system.
    This script now explicitly SKIPS commands.txt, as they are loaded from the database at runtime.
    """
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        logger.error(f"Knowledge base directory not found: '{KNOWLEDGE_BASE_DIR}'")
        return

    logger.info("--- Starting Knowledge Base Ingestion Process (Commands are skipped) ---")

    try:
        # We only need the RAG system part, not the DB part for ingestion
        rag_system = RAGSystem()
        logger.info("RAG system initialized successfully for ingestion.")
    except Exception as e:
        logger.error(f"FATAL: Could not initialize the RAG system: {e}")
        logger.error(traceback.format_exc())
        return

    processed_files = 0
    all_files_in_dir = os.listdir(KNOWLEDGE_BASE_DIR)

    for filename in all_files_in_dir:
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        if not os.path.isfile(file_path) or not filename.lower().endswith('.txt'):
            continue
        
        # --- NEW: EXPLICITLY SKIP commands.txt ---
        if filename == 'commands.txt':
            logger.info(f"Skipping '{filename}' during ingestion. It is handled by the main database.")
            continue

        logger.info(f"--- Processing document: {filename} ---")
        try:
            if filename == 'conversational_rules.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                rule_blocks = content.strip().split('\n---\n')
                for block in rule_blocks:
                    if not block.strip():
                        continue
                    
                    searchable_doc = block.replace('USER_SAYS_VARIANTS:', 'User asks:') \
                                          .replace('BOT_RESPONSE:', 'Bot should answer:') \
                                          .replace('\n', ' ').strip()
                    
                    rule_name_match = re.search(r'\[RULE: (.*?)\]', block)
                    rule_name = rule_name_match.group(1).strip() if rule_name_match else "unknown_rule"

                    rag_system.add_document_chunk(
                        document_text=searchable_doc,
                        source_id=filename,
                        metadata={"source_document": filename, "type": "rule", "rule_name": rule_name}
                    )

            elif filename == 'factual_kb.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                qa_pairs = [pair.strip() for pair in content.strip().split('\n---\n') if pair.strip()]
                for pair in qa_pairs:
                    rag_system.add_document_chunk(
                        document_text=pair,
                        source_id=filename,
                        metadata={"source_document": filename, "type": "fact"}
                    )

            else:
                rag_system.add_document(
                    source_id="global_kb",
                    file_path=file_path,
                    filename=filename
                )

            logger.info(f"✅ Successfully processed and added content from '{filename}'")
            processed_files += 1

        except Exception:
            logger.error(f"❌ An unhandled exception occurred while processing '{filename}'!")
            logger.error(traceback.format_exc())

    if processed_files > 0:
        logger.info(f"✅✅ INGESTION COMPLETE. Processed {processed_files} source files successfully.")
    else:
        logger.warning("❌❌ INGESTION FAILED. No new documents were successfully added.")


if __name__ == '__main__':
    db_dir = "./chroma_db"
    if os.path.exists(db_dir):
        logger.warning(f"Removing existing database directory to ensure a fresh build: {db_dir}")
        shutil.rmtree(db_dir)
        logger.info("Old database removed successfully.")
    
    # We still need to initialize the full RAG system for the chunking methods to work
    initialize_rag_system()
    ingest_knowledge_base()