"""Synthetic symbols for structural validator certification, not a runtime service."""
class IdleAction:
    pass

class IdlePolicy:
    def evaluate(self):
        self.is_eligible()
        self._reset()
        self.is_silent()
        self._silent_for()
        return IdleAction()

    def is_eligible(self):
        return True

    def _reset(self):
        pass

    def clear(self):
        pass

    def is_silent(self):
        return False

    def _silent_for(self):
        return 0
