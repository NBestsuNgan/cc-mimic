from collections import deque
from typing import Any

class LoopDetector:
    def __init__(self):
        self.max_exact_repeat: int = 3
        self.max_cycle_length: int = 5
        self._history: deque = deque(maxlen=20)

    def record_action(self, action_type: str, **details: Any):
        # ["shell|command=echo 'Hello world'"]
        output = [action_type]
        if action_type == "tool_call":
            output.append(details.get("tool_name", ""))
            args = details.get("args", {})

            if isinstance(args, dict):
                for k in sorted(args.keys()):
                    output.append(f"{k}={str(args[k])}")


        elif action_type == "response":
            output.append(details.get("text", ""))
            
        signature = "|".join(output) 
        self._history.append(signature)
    
    def check_for_loop(self) -> str | None:
        # a-b-a-b-a-b
        if len(self._history) < 2:
            return None
        
        # check exact same action
        if len(self._history) >= self.max_exact_repeat:
            recent = self._history[-self.max_exact_repeat:] # a->b->[a->b->a] -> 1 because "a" and "a"
            if len(set(recent)) == 1:
                return f"Same action repeated {self.max_exact_repeat} times"
    
        # check repitition pattern
        if len(self._history) >= self.max_cycle_length * 2:
            history = set(self._history)

            for cyclce_len in range(2, min(self.max_cycle_length + 1, len(history)//2 + 1)): # terminate based on the lenght of history
                recent = history[-cyclce_len*2:]
                if recent[:cyclce_len] == recent[cyclce_len:]:
                    return f"Detected repeating cycle of length {cyclce_len}"
            
        return None
                