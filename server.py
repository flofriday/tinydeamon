from flask import Flask, request, render_template
from index import Index
from time import thread_time_ns

app = Flask(__name__)

index = Index(filename="data.json")


def format_time(ns: int) -> str:
    if ns < 1000:
        return f"{ns}ns"
    elif ns < 1000_000:
        return f"{ns/1000:.2f}μs"
    elif ns < 1000_000_000:
        return f"{ns/1000_000:.2f}ms"
    else:
        return f"{ns/1000_000_000:.2f}s"


@app.route("/")
def home():
    query = request.args.get("q", None)

    if query is None or query.strip() == "":
        return render_template("home.html")

    query = query.strip()
    start = thread_time_ns()
    websites = index.find(query)
    duration = format_time(thread_time_ns() - start)

    return render_template(
        "results.html", duration=duration, query=query, websites=websites
    )
