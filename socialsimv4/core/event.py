class Event:
    def to_string(self, time=None):
        raise NotImplementedError

    def get_sender(self):
        return None


class MessageEvent(Event):
    def __init__(self, sender, message):
        self.sender = sender
        self.message = message

    def to_string(self, time=None):
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}[Message] {self.sender}: {self.message}"

    def get_sender(self):
        return self.sender


class PublicEvent(Event):
    def __init__(self, content):
        self.content = content

    def to_string(self, time=None):
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}Public Event: {self.content}"


class NewsEvent(Event):
    def __init__(self, content):
        self.content = content

    def to_string(self, time=None):
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}[NEWS] {self.content}"


class StatusEvent(Event):
    def __init__(self, status_data):
        self.status_data = status_data

    def to_string(self, time=None):
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}Status: {self.status_data}"


class SpeakEvent(Event):
    def __init__(self, sender, message):
        self.sender = sender
        self.message = message

    def to_string(self, time=None):
        # Natural transcript style: "[time] Alice: message"
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}{self.sender}: {self.message}"

    def get_sender(self):
        return self.sender


class WebSearchEvent(Event):
    def __init__(self, sender, query):
        self.sender = sender
        self.query = query

    def to_string(self, time=None):
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}{self.sender} searched: {self.query}"

    def get_sender(self):
        return self.sender


class ViewPageEvent(Event):
    def __init__(self, sender, url):
        self.sender = sender
        self.url = url

    def to_string(self, time=None):
        time_str = f"[{time}:00] " if time is not None else ""
        return f"{time_str}{self.sender} viewed web page: {self.url}"

    def get_sender(self):
        return self.sender
