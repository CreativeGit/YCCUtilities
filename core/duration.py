class DurationConverter:
    def __init__(self, duration_str: str):
        self.duration_str = duration_str

    def get_resolved_duration(self):
        if self.duration_str.lower() in 'permanent':
            return 1000000000

        duration_converter = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'y': 31536000}

        try:
            duration_resolved = int(self.duration_str[:-1]) * duration_converter[self.duration_str[-1:].lower()]
            return duration_resolved
        except (ValueError, KeyError):
            return None
