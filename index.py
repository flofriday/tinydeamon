from typing import Any, Dict, List, Optional, Set, Tuple, Union
import os
import json
import re
import math


class Website:
    """
    The datastructure that represents a website
    """

    def __init__(
        self,
        url: str,
        name: str,
        description: str,
        icon: str,
        word_count: Optional[int] = 0,
    ):
        self.url = url
        self.name = name
        self.description = description
        self.icon = icon
        self.word_count = word_count


class Index:
    """
    The index is the datastructure that enables the searchengine to do fast
    query lookups.
    """

    def __init__(
        self, filename: Optional[Union[os.PathLike[Any], str, bytes]] = None
    ):

        # TODO: improve this split regex, I don't like that i its more an
        # educated guess than a well defined delimiter
        self._split_regex = re.compile("[\\s\\.,;:?!\"'\\-_/\\(\\)]+")

        if filename is None:
            self.websites: List[Website] = []
            self.words: Dict[str, Dict[int, List[int]]] = dict()
            self.avg_length: float = 0.0
            return

        with open(filename) as file:
            data = json.load(file)
            self.websites = list(
                map(
                    lambda d: Website(
                        d["url"],
                        d["name"],
                        d["description"],
                        d["icon"],
                        word_count=d["word_count"],
                    ),
                    data["websites"],
                )
            )
            self.words = dict()
            for k, v in data["words"].items():
                self.words[k] = dict()
                for k2, v2 in v.items():
                    self.words[k][int(k2)] = v2
            self.avg_length = data["avg_length"]

    def _normlize_split_text(self, text: str) -> List[str]:
        """
        This method normalizes the input text (lowercase) and splits it into
        words.
        """
        text = text.lower()
        words = self._split_regex.split(text)
        return words

    def add_website(self, website: Website, text: str):
        """
        Add a website to the index.

        Runtime: O(n) with n beeing the number of words that are associated
        with the website.
        """

        index = len(self.websites)
        words = self._normlize_split_text(text)
        website.word_count = len(words)
        self.websites.append(website)

        for i, word in enumerate(words):
            try:
                self.words[word][index].append(i)
            except KeyError:
                try:
                    self.words[word][index] = [i]
                except KeyError:
                    self.words[word] = {index: [i]}

    def _rank_bm25(
        self,
        ids: List[int],
        query: List[str],
    ) -> List[int]:
        """
        This is an implemetation of the Okapi BM25 algorithm. It only checks
        how good a document and a query matches, but asumes all documents have
        the same quality (which of course isn't the case on the web).

        Wikipedia: https://en.wikipedia.org/wiki/Okapi_BM25
        """
        ranked: List[Tuple[int, float]] = list()

        # Assign ever document a score
        N = len(self.websites)  # Number of documents
        avgdl = self.avg_length

        k1 = 1.2  # Tuning variable
        b = 0.75  # Tuning variable
        for id in ids:
            score = 0  # Score of the current document (id)

            D_abs = self.websites[id].word_count
            for qi in query:
                try:
                    f = len(self.words[qi][id])  # Term frequenncy of qi in d
                except KeyError:
                    f = 0
                n = len(self.words[qi])  # Number of documents containing qi

                # inverse term frequency
                idf = math.log((N - n + 0.51) / (n + 0.5) + 1)

                score += idf * (
                    (f * (k1 + 1)) / (f + k1 * (1 - b + b * (D_abs / avgdl)))
                )

            ranked.append((id, score))

        # Sort by the score
        ranked = sorted(ranked, key=lambda d: d[1], reverse=True)
        return list(map(lambda d: d[0], ranked))

    def find(self, query: str) -> List[Website]:
        """
        Find results for a query.
        """

        words = self._normlize_split_text(query)
        ids: Set[int] = set()

        # Find all sites that have at least one word of the query
        for word in words:
            try:
                current_ids = self.words[word].keys()
                ids.update(current_ids)
            except KeyError:
                continue

        # Rank the results to show the best on top
        ids = self._rank_bm25(list(ids), words)
        websites = list(map(lambda i: self.websites[i], ids))
        return websites

    def save(
        self,
        filename: Union[os.PathLike[Any], str, bytes],
        debug: Optional[bool] = False,
    ):
        # Create a new object, so that only necessary data will be saved
        obj = dict()
        obj["websites"] = self.websites
        obj["words"] = self.words
        obj["avg_length"] = sum(
            map(lambda w: w.word_count, self.websites)
        ) / len(self.websites)

        with open(filename, "w") as file:
            json.dump(
                obj,
                file,
                indent=2 if debug else None,
                default=lambda o: o.__dict__,
                ensure_ascii=False,
            )
