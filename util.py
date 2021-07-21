def format_time(ns: int) -> str:
    sec = 1000_000_000
    if ns < 1000:
        return f"{ns}ns"
    elif ns < 1000_000:
        return f"{ns/1000:.2f}μs"
    elif ns < 1000_000_000:
        return f"{ns/1000_000:.2f}ms"
    elif ns < 60 * sec:
        return f"{ns/sec:.2f}s"
    elif ns < 60 * 60 * sec:
        return f"{ns/(sec*60):.2f}min"
    else:
        return f"{ns/(sec*60*60):.2f}h"
