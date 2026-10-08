def average(numbers):
    if not numbers:
        raise ValueError('numbers must not be empty')
    return sum(numbers) / len(numbers)


def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
