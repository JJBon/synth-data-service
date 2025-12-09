
import sys

print("Start input test")
try:
    while True:
        sys.stdout.write("Prompt: ")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            break
        print(f"Received: {repr(line)}")
except KeyboardInterrupt:
    pass
