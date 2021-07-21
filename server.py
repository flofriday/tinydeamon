from flask import Flask, request, render_template
from index import Index
from time import time_ns
from util import format_time

app = Flask(__name__)

index = Index("data/")


@app.route("/")
def home():
    query = request.args.get("q", None)

    if query is None or query.strip() == "":
        return render_template("home.html")

    query = query.strip()
    start = time_ns()
    websites = index.find(query)
    duration = format_time(time_ns() - start)

    return render_template(
        "results.html", duration=duration, query=query, websites=websites
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404
