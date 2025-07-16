# Simple calculator with some issues
def calculate(x, y, operation):
    if operation == "add":
        return x + y
    elif operation == "subtract":
        return x - y
    elif operation == "multiply":
        return x * y
    elif operation == "divide":
        return x / y  # No error handling for division by zero!
    else:
        return "Invalid operation"


# Main execution without proper structure
if __name__ == "__main__":
    result1 = calculate(10, 5, "add")
    print(f"10 + 5 = {result1}")

    result2 = calculate(10, 0, "divide")  # This will cause a ZeroDivisionError!
    print(f"10 / 0 = {result2}")

    result3 = calculate(5, 3, "power")  # Invalid operation
    print(f"5 ^ 3 = {result3}")
