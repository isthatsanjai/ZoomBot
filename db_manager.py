import psycopg2
from psycopg2 import pool
from config import Config
import logging

logger = logging.getLogger(__name__)
db_pool = None

def initialize_db_pool():
    """Initializes the connection pool."""
    global db_pool
    if db_pool:
        return  
    try:
        logger.info("Initializing database connection pool...")
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            dbname=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            host=Config.DB_HOST,
            port=Config.DB_PORT
        )
        logger.info("✅ Database connection pool initialized successfully.")
    except psycopg2.OperationalError as e:
        logger.error(f"FATAL: Could not connect to PostgreSQL. Is the Docker container running? Error: {e}")
        db_pool = None

def get_connection():
    """Gets a connection from the pool."""
    if not db_pool:
        raise Exception("Database pool is not initialized. Cannot get connection.")
    return db_pool.getconn()

def release_connection(conn):
    """Releases a connection back to the pool."""
    db_pool.putconn(conn)

def get_host_commands():
    """Fetches active host commands directly from the database."""
    conn = get_connection()
    commands = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT command_name, trigger_phrases, broadcast_message, ack_message FROM commands WHERE is_active = TRUE;")
            rows = cur.fetchall()
            for row in rows:
                commands.append({
                    "name": row[0],
                    "triggers": row[1], # Already an array from the DB
                    "broadcast_message": row[2],
                    "ack_message": row[3]
                })
        logger.info(f"Loaded {len(commands)} commands from the database.")
    except Exception as e:
        logger.error(f"Error fetching commands from database: {e}")
    finally:
        release_connection(conn)
    return commands

def log_chat_interaction(meeting_id, user_id, user_name, user_role, user_chat, chat_type, bot_classification, bot_response):
    """Logs a complete chat interaction to the database."""
    # First, ensure the user and meeting exist.
    upsert_user(user_id, user_name)
    upsert_meeting(meeting_id)
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO chat_logs (meeting_id, user_id, user_chat, user_role, chat_type, bot_classification, bot_response)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            # IMPORTANT: Use parameterized queries to prevent SQL injection!
            cur.execute(sql, (meeting_id, user_id, user_chat, user_role, chat_type, bot_classification, bot_response))
            conn.commit()
            logger.info(f"Logged chat from user {user_id} in meeting {meeting_id}.")
    except Exception as e:
        logger.error(f"Error logging chat to database: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def upsert_user(user_id, user_name, user_email=None):
    """Creates a user if they don't exist, or updates their name if they do."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO users (user_id, user_name, user_email)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET user_name = EXCLUDED.user_name;
            """
            cur.execute(sql, (user_id, user_name, user_email))
            conn.commit()
    except Exception as e:
        logger.error(f"Error upserting user {user_id}: {e}")
        conn.rollback()
    finally:
        release_connection(conn)
        
def upsert_meeting(meeting_id):
    """Creates a meeting record if it doesn't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "INSERT INTO meetings (meeting_id) VALUES (%s) ON CONFLICT (meeting_id) DO NOTHING;"
            cur.execute(sql, (meeting_id,))
            conn.commit()
    except Exception as e:
        logger.error(f"Error upserting meeting {meeting_id}: {e}")
        conn.rollback()
    finally:
        release_connection(conn)