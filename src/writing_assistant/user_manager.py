import json
import os
from typing import Dict, Any, List


class UserManager:
    """Simple user management with memories."""
    
    def __init__(self, file_path: str = "data/users.json"):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create the JSON file if it doesn't exist."""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_data(self, data: Dict[str, Any]):
        """Save data to JSON file."""
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user data, create if doesn't exist."""
        data = self._load_data()
        if user_id not in data:
            data[user_id] = {"memories": []}
            self._save_data(data)
        return data[user_id]
    
    def get_memories(self, user_id: str) -> List[str]:
        """Get user's memories."""
        user = self.get_user(user_id)
        return user.get("memories", [])
    
    def add_memory(self, user_id: str, memory: str):
        """Add a memory to user."""
        data = self._load_data()
        if user_id not in data:
            data[user_id] = {"memories": []}
        
        if "memories" not in data[user_id]:
            data[user_id]["memories"] = []
        
        data[user_id]["memories"].append(memory)
        self._save_data(data)
    
    def get_all_users(self) -> List[str]:
        """Get list of all user IDs."""
        data = self._load_data()
        return list(data.keys())

if __name__ == "__main__":
    user_manager = UserManager()
    print(user_manager.get_memories("sample_user_123"))