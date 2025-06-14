"""
main.py

Entry point for the sample_project package. Demonstrates usage of math_helpers.
"""

from sample_project.utils.math_helpers import add, multiply

def main():
    x = 3.5
    y = 2.0
    sum_result = add(x, y)
    product_result = multiply(x, y)
    print(f"The sum of {x} and {y} is {sum_result}")
    print(f"The product of {x} and {y} is {product_result}")

if __name__ == "__main__":
    main()
