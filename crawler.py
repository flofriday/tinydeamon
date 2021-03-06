from os import removedirs
from index import Index, Website
from typing import List, Set, Tuple
import argparse
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urldefrag, urljoin
import concurrent.futures
from util import format_time
from time import time_ns


def print_header(text: str):
    """
    Prints the text with `-` characters left and right to create a header
    """
    text = "\n" + "-" * int(40 - len(text) / 2) + text
    text += "-" * int(80 - len(text))
    print(text)


def download(url: str) -> Tuple[str, BeautifulSoup]:
    """
    Download a url and return the final url (after redirects) and the
    bs4 parsed html structure
    """
    headers = {
        "Accept-Language": "en-US",
        "User-Agent": "tinyDeamon crawler (https://tinyDeamon.com)",
    }

    # TODO: also throw exception if an image/pdf is returned
    resp = requests.get(url, headers=headers, timeout=5)
    if resp.status_code != 200:
        raise Exception(f"Server returned status {resp.status_code}")
    body = resp.text
    new_url = resp.url

    soup = BeautifulSoup(body, "html.parser")
    return new_url, soup


def extract_metadata(url: str, body: BeautifulSoup) -> Website:
    """
    Extract metadata from a site and put it into a `Website object`.
    """
    try:
        name = body.title.get_text().strip()
    except AttributeError:
        name = url

    try:
        description = (
            body.find(attrs={"name": "description"}).get("content").strip()
        )
    except AttributeError:
        description = extract_text(body)[:400] + "..."

    try:
        icon = urljoin(url, body.find("link", rel="icon").get("href"))
    except AttributeError:
        # As Browsers do, if the html doesn't specify an icon we will just try
        # the default path
        icon = urljoin(url, "/favicon.ico")

    return Website(
        url,
        name,
        description,
        icon,
    )


def extract_links(url: str, body: BeautifulSoup) -> Set[str]:
    """
    Extract all links from a document and return a unique set of those links
    """
    links = []
    for link in body.find_all("a"):
        link, _ = urldefrag(urljoin(url, link.get("href")))
        links.append(link)
    return set(links)


def extract_text(body: BeautifulSoup) -> str:
    """
    Extract all text from the page.
    """
    return body.get_text()


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
        help="limit of number websites to be crawled (default: 10)",
    )
    parser.add_argument(
        "--output",
        default="data/",
        type=str,
        help="directory name in which to store the index (default: data/)",
    )
    parser.add_argument(
        "seed",
        type=str,
        nargs="+",
        help="list of websites to start crawling with",
    )
    args = parser.parse_args()

    # Extract configuration
    limit = args.limit
    queue: List[str] = args.seed
    index_dir = args.output
    index = Index(index_dir, limit * 10, delete_existing=True)

    seen: Set[str] = set()
    explored: Set[str] = set()
    num_concurrent = 64
    print_header("Configuration")
    print(f"- Downloading {limit} websites")
    print(f"- Website seed: {queue}")
    print(f"- Outputdirectory: {index_dir}")

    # Main loop to discover, process and add new websites
    start = time_ns()
    print_header("Downloading")
    while len(index.websites) < limit and len(queue) > 0:
        num_urls = limit - len(index.websites)
        urls, queue = queue[:num_urls], queue[num_urls:]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_concurrent
        ) as executor:
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

                if new_url in explored:
                    # The url redirected to new_url a page we already explored
                    continue

                # Add the current page to the index
                website = extract_metadata(new_url, body)
                words = extract_text(body)
                index.add_website(website, words)

                # Update crawlers internal data to add new discoverd links but
                # make sure we never download a page twice
                links = extract_links(new_url, body)
                links = filter(lambda l: l not in seen, links)
                queue.extend(links)
                seen.add(new_url)
                seen.update(links)
                explored.add(url)
                explored.add(new_url)

                logging.info(
                    f"[{len(index.websites)}/{limit}] Downloaded {new_url}"
                )

    # Write the index to disk
    logging.info("Saving index...")
    index.save()
    logging.info("Saved index")

    duration = time_ns() - start
    print_header("Statistics")
    print(f"- Indexed Websites: {len(index.websites)}")
    print(f"- Indexed Words: {index.word_count}")
    print(f"- Duration: {format_time(duration)}")
    print(
        f"- Avg Duration/Websites: {format_time(duration/len(index.websites))}"
    )
    print(f"- Websites in queue: {len(queue)}")
    print(f"- Saved in: {index_dir}")


if __name__ == "__main__":
    main()
    # with cProfile.Profile() as prof:
    #     main()

    # stats = pstats.Stats(prof)
    # stats.sort_stats(pstats.SortKey.TIME)
    # stats.dump_stats(filename="crawler.prof")
