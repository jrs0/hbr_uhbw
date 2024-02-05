def foo():
    """Print Foo
    
    Examples:
        >>> from pyhbr.example import foo
        >>> foo()
        Foo ran
    
    """
    print("Foo ran")
    
def bar(x):
    """Bar returns x + 1

    Examples:
        >>> from pyhbr.example import bar
        >>> bar(3)
        4

    Args:
        x (int): The value to use
    """
    return x+1