
import json
import os

def init_db():
    """Initialize database (JSON files) for the Telegram bot."""
    try:
        # Initialize scores.json if it doesn't exist
        if not os.path.exists("scores.json"):
            with open("scores.json", "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)
            print("scores.json initialized successfully!")
        
        # Initialize players.json if it doesn't exist
        if not os.path.exists("players.json"):
            with open("players.json", "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False)
            print("players.json initialized successfully!")
        
        print("Database files initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def get_scoreboard(chat_id):
    """Get scoreboard for a specific chat."""
    try:
        with open("scores.json", "r", encoding="utf-8") as f:
            scoreboard = json.load(f)
        return scoreboard.get(chat_id, {})
    except FileNotFoundError:
        return {}

def get_player_names():
    """Get all player names."""
    try:
        with open("players.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def backup_data():
    """Create backup of current data files."""
    import shutil
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        if os.path.exists("scores.json"):
            shutil.copy("scores.json", f"scores_backup_{timestamp}.json")
        if os.path.exists("players.json"):
            shutil.copy("players.json", f"players_backup_{timestamp}.json")
        print(f"Data backup created with timestamp: {timestamp}")
    except Exception as e:
        print(f"Error creating backup: {e}")
