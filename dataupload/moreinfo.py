# Get more information about the user
from typing import Dict, Any


class MoreInfo:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_more_info(self) -> Dict[str, Any]:
        info = input("Do you have any more info you will want the agent to know about you?: ")
        goals = input("What are your goals for each agent?: ")
        return {
            "user_id": self.user_id,
            "info": info,
            "goals": goals,
        }