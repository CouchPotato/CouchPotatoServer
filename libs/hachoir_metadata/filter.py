from hachoir_metadata.timezone import UTC
from datetime import date, datetime

# Year in 1850..2030
MIN_YEAR = 1850
MAX_YEAR = 2030

class Filter:
    def __init__(self, valid_types, min=None, max=None):
        self.types = valid_types
        self.min = min
        self.max = max

    def __call__(self, value):
        if not isinstance(value, self.types):
            return True
        if self.min is not None and value < self.min:
            return False
        if self.max is not None and self.max < value:
            return False
        return True

class NumberFilter(Filter):
    def __init__(self, min=None, max=None):
        Filter.__init__(self, (int, long, float), min, max)

class DatetimeFilter(Filter):
    def __init__(self, min=None, max=None):
        Filter.__init__(self, (date, datetime),
            datetime(MIN_YEAR, 1, 1),
            datetime(MAX_YEAR, 12, 31))
        self.min_date = date(MIN_YEAR, 1, 1)
        self.max_date = date(MAX_YEAR, 12, 31)
        self.min_tz = datetime(MIN_YEAR, 1, 1, tzinfo=UTC)
        self.max_tz = datetime(MAX_YEAR, 12, 31, tzinfo=UTC)

    def __call__(self, value):
        """
        Use different min/max values depending on value type
        (datetime with timezone, datetime or date).
        """
        if not isinstance(value, self.types):
            return True
        if hasattr(value, "tzinfo") and value.tzinfo:
            return (self.min_tz <= value <= self.max_tz)
        elif isinstance(value, datetime):
            return (self.min <= value <= self.max)
        else:
            return (self.min_date <= value <= self.max_date)

DATETIME_FILTER = DatetimeFilter()

