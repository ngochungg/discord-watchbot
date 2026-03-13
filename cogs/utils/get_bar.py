class Bar:
    def __init__(self, percent: float, length: int = 20):
        self.percent = percent
        self.length = length

    @staticmethod
    def get_bar(percent):
        filled = int(percent / 10)
        return "█" * filled + "░" * (10 - filled)