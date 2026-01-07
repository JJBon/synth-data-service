
from fastmcp import FastMCP, Context
import inspect

print("FastMCP dir:")
print(dir(FastMCP))

print("\nContext dir:")
print(dir(Context))

# Check if we can see how Context is defined or if there are other relevant classes
try:
    print("\nContext source/doc:")
    print(Context.__doc__)
except:
    pass

