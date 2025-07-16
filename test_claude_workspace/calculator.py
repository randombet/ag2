def add(a, b):
    return a + b


def divide(a, b):
    return a / b  # No error handling


if __name__ == "__main__":
    print(add(5, 3))
    print(divide(10, 0))  # This will crash!
