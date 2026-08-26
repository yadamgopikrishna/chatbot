import os
import sys

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from db import get_connection, is_oracle

def display_database_users():
    print("=" * 80)
    print("          OG AI ASSISTANT — DATABASE USER & ACTIVITY INSPECTOR")
    print("=" * 80)
    
    conn = get_connection()
    is_ora = is_oracle()
    cursor = conn.cursor()
    
    db_name = "Oracle Database 11g XE" if is_ora else "SQLite (database/chatbot.db)"
    print(f"Connected Database: {db_name}\n")
    
    try:
        # 1. Fetch Registered Users
        print("-" * 80)
        print("📌 REGISTERED USERS")
        print("-" * 80)
        
        if is_ora:
            cursor.execute("SELECT column_name FROM user_tab_columns WHERE table_name = 'USERS'")
            cols = [row[0].upper() for row in cursor.fetchall()]
            
            has_api_key = "API_KEY" in cols
            query = "SELECT user_id, name, email, created_date, preferred_lang, theme"
            if has_api_key:
                query += ", api_key"
            query += " FROM users ORDER BY user_id ASC"
            
            cursor.execute(query)
            users = cursor.fetchall()
            
            if not users:
                print("No registered users found in database.")
            else:
                print(f"{'ID':<5} | {'NAME':<20} | {'EMAIL':<30} | {'REGISTERED':<16}")
                print("-" * 80)
                for u in users:
                    uid = u[0]
                    name = str(u[1])[:18]
                    email = str(u[2])[:28]
                    reg_date = str(u[3])[:10] if u[3] else "N/A"
                    print(f"{uid:<5} | {name:<20} | {email:<30} | {reg_date:<16}")
        else:
            cursor.execute("SELECT user_id, name, email, created_date, preferred_lang, theme FROM users ORDER BY user_id ASC")
            users = cursor.fetchall()
            if not users:
                print("No registered users found in database.")
            else:
                print(f"{'ID':<5} | {'NAME':<20} | {'EMAIL':<30} | {'REGISTERED':<16}")
                print("-" * 80)
                for u in users:
                    uid = u[0] if isinstance(u, tuple) else u["user_id"]
                    name = (u[1] if isinstance(u, tuple) else u["name"])[:18]
                    email = (u[2] if isinstance(u, tuple) else u["email"])[:28]
                    reg = str(u[3] if isinstance(u, tuple) else u["created_date"])[:10]
                    print(f"{uid:<5} | {name:<20} | {email:<30} | {reg:<16}")

        print(f"\nTotal Registered Users: {len(users)}\n")

        # 2. Fetch User Activity (Conversations & Recent Actions)
        print("-" * 80)
        print("💬 RECENT ACTIVITY & CONVERSATIONS")
        print("-" * 80)

        if is_ora:
            cursor.execute("""
                SELECT user_email, COUNT(conversation_id) as total_chats, MAX(updated_at) as last_active
                FROM conversations
                GROUP BY user_email
                ORDER BY last_active DESC
            """)
            activity = cursor.fetchall()
            if not activity:
                print("No conversations recorded yet.")
            else:
                print(f"{'USER EMAIL':<32} | {'CHATS':<8} | {'LAST ACTIVE'}")
                print("-" * 80)
                for act in activity:
                    email = str(act[0])[:30]
                    chats = act[1]
                    last_act = str(act[2])[:19] if act[2] else "N/A"
                    print(f"{email:<32} | {chats:<8} | {last_act}")
        else:
            cursor.execute("""
                SELECT user_email, COUNT(conversation_id) as total_chats, MAX(updated_at) as last_active
                FROM conversations
                GROUP BY user_email
                ORDER BY last_active DESC
            """)
            activity = cursor.fetchall()
            if not activity:
                print("No conversations recorded yet.")
            else:
                print(f"{'USER EMAIL':<32} | {'CHATS':<8} | {'LAST ACTIVE'}")
                print("-" * 80)
                for act in activity:
                    email = (act[0] if isinstance(act, tuple) else act["user_email"])[:30]
                    chats = act[1] if isinstance(act, tuple) else act["total_chats"]
                    last_act = str(act[2] if isinstance(act, tuple) else act["last_active"])[:19]
                    print(f"{email:<32} | {chats:<8} | {last_act}")

        print("=" * 80)

    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    display_database_users()
