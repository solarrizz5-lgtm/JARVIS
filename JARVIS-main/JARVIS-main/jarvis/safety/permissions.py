from jarvis import config
from jarvis.utils.logger import log_info, log_error

def is_command_blocked(command: str) -> bool:
    """
    Evaluates the user's command against security restrictions.
    Returns True if the command is blocked, False otherwise.
    """
    if not command:
        return False
        
    command_lower = command.lower()
    
    for phrase in config.BLOCKED_GOAL_PHRASES:
        if phrase in command_lower:
            log_error(f"Security override triggered. Blocked phrase matched: '{phrase}'")
            return True
            
    return False

def requires_confirmation(action_type: str) -> bool:
    """
    Future expansion: Determine if a specific GUI action (like 'delete') 
    requires the user to verbally confirm before execution.
    """
    high_risk_actions = ["delete", "format", "purchase"]
    return action_type in high_risk_actions