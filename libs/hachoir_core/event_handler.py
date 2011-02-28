class EventHandler(object):
    """
    Class to connect events to event handlers.
    """

    def __init__(self):
        self.handlers = {}

    def connect(self, event_name, handler):
        """
        Connect an event handler to an event. Append it to handlers list.
        """
        try:
            self.handlers[event_name].append(handler)
        except KeyError:
            self.handlers[event_name] = [handler]

    def raiseEvent(self, event_name, *args):
        """
        Raiser an event: call each handler for this event_name.
        """
        if event_name not in self.handlers:
            return
        for handler in self.handlers[event_name]:
            handler(*args)

