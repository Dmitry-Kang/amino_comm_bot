def contains(list, filter):
    for x in list:
        if filter(x):
            return True
    return False

def count(list, filter):
    res = 0
    for x in list:
        if filter(x):
            res = res + 1
    return res

def is_int(str):
    try:
        int(str)
        return True
    except ValueError:
        return False