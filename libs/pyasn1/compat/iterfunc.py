from sys import version_info

if version_info[0] <= 2 and version_info[1] <= 4:
    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True
else:
    all = all
