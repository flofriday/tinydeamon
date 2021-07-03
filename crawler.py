from index import Index, Website
from typing import List, Set, Tuple
import argparse
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urldefrag, urljoin
import concurrent.futures


def download(url: str) -> Tuple[str, BeautifulSoup]:
    resp = requests.get(url)
    if resp.status_code != 200:
        # TODO: improve
        raise Exception()

    body = resp.text
    soup = BeautifulSoup(body, "html.parser")

    return resp.url, soup


def extractMetadata(url: str, body: BeautifulSoup) -> Website:

    try:
        name = body.title.get_text()
    except AttributeError:
        name = url

    try:
        description = body.find(attrs={"name": "description"}).get("content")
    except AttributeError:
        description = ""

    try:
        icon = urljoin(url, body.find("link", rel="icon").get("href"))
    except AttributeError:
        icon = None

    return Website(
        url,
        name,
        description,
        icon,
    )


def extractLinks(url: str, body: BeautifulSoup) -> List[str]:
    links = []
    for link in body.find_all("a"):
        link, _ = urldefrag(urljoin(url, link.get("href")))
        links.append(link)
    return links


def extractWords(body: BeautifulSoup) -> List[str]:
    # TODO: remove punktuation from words
    words = body.get_text().split()
    words = map(lambda w: w.lower(), words)
    return list(set(words))


def main():
    logging.basicConfig(
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Setup the CLI interface
    parser = argparse.ArgumentParser(description="Tinydeamon's crawler")
    parser.add_argument(
        "--limit",
        default=10,
        type=int,
        help="Limit of number websites to be crawled",
    )
    parser.add_argument(
        "seed",
        type=str,
        nargs="+",
        help="list of websites to start crawling with",
    )
    args = parser.parse_args()

    # Main loop to discover, process and add new websites
    index = Index()
    limit = args.limit
    queue: List[str] = args.seed
    explored: Set[str] = set()
    num_concurrent = 64

    while len(index.websites) < limit and len(queue) > 0:
        num_urls = min(limit - len(index.websites), num_concurrent)
        urls, queue = queue[:num_urls], queue[num_urls:]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_url = {
                executor.submit(download, url): url for url in urls
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    new_url, body = future.result()
                except Exception as exc:
                    logging.warning(
                        "%r generated an exception: %s" % (url, exc)
                    )
                    continue

                if url in explored:
                    continue

                # new_url, body = download(url)
                website = extractMetadata(new_url, body)
                words = extractWords(body)
                index.add_website(website, words)

                links = extractLinks(new_url, body)
                queue.extend(links)
                explored.add(url)
                explored.add(new_url)
                logging.info(f"Downloaded {new_url}")

    index.save("data.txt")


if __name__ == "__main__":
    main()