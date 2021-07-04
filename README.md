# tinydeamon

![Screenshot](screenshot.png)
An experimental search engine

## Run it locally

### Requirements

1. You will need a recent version of [python](https://www.python.org/downloads/) (preferable 3.9)
2. I would recommend using [python's virtual environments](https://docs.python.org/3/library/venv.html)

**Unix:**

```
python3 -m venv venv
source venv/bin/activate
```

**Windows:**

```
py -3 -m venv venv
venv\Scripts\activate
```

3. Lastly, you will need to install the dependencies with
   `pip install -r requirements.txt`

### Crawler

The crawler takes two arguments, first the number of websites it should crawl,
and a list of websites with which it should start (this is often called the seed).

For example to index 20 pages, starting with GitHub and BBC we can run:

```
python3 crawler.py --limit 20 https://github.com https://www.bbc.com/
```

### Server

```
FLASK_APP=server flask run
```

**Note:** this will spawn only a development server which is not suited for
production. Read [this page](https://flask.palletsprojects.com/en/2.0.x/tutorial/deploy/)
in flasks documentation on how to deploy a flask app.
