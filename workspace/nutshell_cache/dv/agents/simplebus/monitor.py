"""Subscriber hub for observed protocol transactions."""
class SimpleBusMonitor:
    def __init__(self, channel="unknown"):
        self.channel = channel
        self.subscribers = []
        self.transactions = []

    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)

    def publish(self, transaction):
        self.transactions.append(transaction)
        for subscriber in self.subscribers:
            channel_callback = getattr(subscriber, "write_channel", None)
            if channel_callback:
                channel_callback(self.channel, transaction)
            else:
                callback = getattr(subscriber, "write", subscriber)
                callback(transaction)
