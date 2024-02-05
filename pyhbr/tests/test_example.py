import pyhbr.example as e

def test_bar():
    for n in range(100):
        e.bar(n) == n+1