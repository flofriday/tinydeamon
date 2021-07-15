from typing import Any, Dict, List, Optional, Set, Tuple, Union
import os
import json
import re
import math
import hashlib
import concurrent.futures
import tempfile


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

    Understanding the datastructure is not trivial so here is a simple
    introduction to how it works and the used terminology.

    What a website is, is quite self-explainatory. Every website is saved
    in an sequetial array and has therefore an index inside that array, in this
    class we use the term `web_id` to for that index (because the whole thing
    is and index and we want to avoid confusion).

    Next there is the "real" index which maps the words to a list of entries.
    Every entry stores in which document it is stored and where in the document
    the word appreas in.
    This index is called `words` and has the type:

             words: Dict[str, Dict[int, List[int]]]
                          ▲         ▲      ▲
                          │         │      │
                        word     web_id   positions

    At first it may look confusing but this makes it increadibly hard to look
    up in which documents a word appreas and where in a document a word
    appreas.

    Next, the whole index is never in memory. While building the index
    the class uses `self.words` to store a part of the index and will flush it
    out when it hits a certian threshold.
    So the index is split in so called `segments`, and each segments has one or
    more rows, and each row is a record. Than each record, starts with the
    word, followed by a colon and a list of entries. Each entry is surrounded
    by brackets, and has one web_id and the positions where the word appears
    in the website. Here is a simple example:

                    hello:[1|28][13|2,34,5843]
                    ▲▲▲▲▲ ▲▲▲▲▲▲ ▲▲ ▲▲▲▲▲▲▲▲▲
                    └┬──┘ └─┬──┘ └┐ └────┬──┘
                     │      │     │      │
                    word    │     │  positions
                            │     │
                        entry   web_id
    """

    def __init__(self, directory: str):

        # TODO: improve this split regex, I don't like that i its more an
        # educated guess than a well defined delimiter
        self._split_regex = re.compile("[\\s\\.,;:?!\"'\\-_/\\(\\)]+")
        self.directory: str = directory
        self.websites_file: str = os.path.join(directory, "websites.json")
        self.config_file: str = os.path.join(directory, "config.json")
        self.words: Dict[str, Dict[int, List[int]]] = dict()
        self.unsaved_words: int = 0
        self.word_count: int = 0

        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            self.websites: List[Website] = []
            self.avg_length: int = 0

        else:
            with open(self.websites_file) as file:
                self.websites = self.websites = list(
                    map(
                        lambda d: Website(
                            d["url"],
                            d["name"],
                            d["description"],
                            d["icon"],
                            word_count=d["word_count"],
                        ),
                        json.load(file),
                    )
                )

            with open(self.config_file) as file:
                config = json.load(file)
                self.avg_length = config["avg_length"]
                self.word_count = config["word_count"]

    def _normlize_split_text(self, text: str) -> List[str]:
        """
        This method normalizes the input text (lowercase) and splits it into
        words.
        """
        text = text.lower()
        words = self._split_regex.split(text)
        return words

    def _segment_name(self, word: str) -> str:
        # TODO: the first 6 segments should not be hardcoded but
        # be configurable
        return (hashlib.md5(word.encode("utf-8"))).hexdigest()[:6]

    def _segment_to_filename(self, segment_name: str) -> str:
        return os.path.join(self.directory, segment_name + ".index")

    def add_website(self, website: Website, text: str):
        """
        Add a website to the index.

        Runtime: O(n) with n beeing the number of words that are associated
        with the website.

        Note: this method might write to disk, so some calls might be much
        slower than others. To force a disk-write call `save`.
        """

        web_id = len(self.websites)
        words = self._normlize_split_text(text)
        website.word_count = len(words)
        self.websites.append(website)
        self.unsaved_words += len(words)
        self.word_count += len(words)

        for i, word in enumerate(words):
            try:
                self.words[word][web_id].append(i)
            except KeyError:
                try:
                    self.words[word][web_id] = [i]
                except KeyError:
                    self.words[word] = {web_id: [i]}

        if self.unsaved_words >= 1000:
            self._save_words()

    def _rank_bm25(
        self,
        index: Dict[str, Dict[int, List[int]]],
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
                    f = len(index[qi][id])  # Term frequenncy of qi in d
                except KeyError:
                    f = 0
                n = len(index[qi])  # Number of documents containing qi

                # inverse term frequency
                idf = math.log((N - n + 0.51) / (n + 0.5) + 1)

                score += idf * (
                    (f * (k1 + 1)) / (f + k1 * (1 - b + b * (D_abs / avgdl)))
                )

            ranked.append((id, score))

        # Sort by the score
        ranked = sorted(ranked, key=lambda d: d[1], reverse=True)
        print(ranked)
        return list(map(lambda d: d[0], ranked))

    def _parse_entries(self, entries: str) -> Dict[int, List[int]]:
        # TODO: precompile
        entry_list = re.findall("\\[([0-9]+)\\|([0-9,]+)\\]", entries)

        result = dict()
        for web_id, positions in entry_list:
            result[int(web_id)] = list(
                map(lambda p: int(p), positions.split(","))
            )

        return result

    def _load_segment(self, word) -> Dict[int, List[int]]:
        seg_filename = self._segment_to_filename(self._segment_name(word))

        if os.path.exists(seg_filename):
            with open(seg_filename) as segment:
                for line in segment:
                    w, entries = self._parse_record(line)
                    if w == word:
                        return self._parse_entries(entries)

        return dict()

    def find(self, query: str) -> List[Website]:
        """
        Find results for a query.
        """

        words = self._normlize_split_text(query)
        ids: Set[int] = set()
        index = dict()

        # Find all sites that have at least one word of the query
        for word in words:
            # TODO: Load this in paralell with threadpool
            index[word] = self._load_segment(word)

            try:
                current_ids = index[word].keys()
                ids.update(current_ids)
            except KeyError:
                continue

        # Rank the results to show the best on top
        ids = self._rank_bm25(index, list(ids), words)
        websites = list(map(lambda i: self.websites[i], ids))
        return websites

    def _parse_record(self, record: str) -> Tuple[str, str]:
        lst = record.split(":")
        return (lst[0], lst[1])

    def _save_segment(self, segment_name: str, entries: List[Tuple[str, str]]):
        # Sort the entries alphabetically
        entries = sorted(entries, key=lambda e: e[0])

        new_segment = tempfile.NamedTemporaryFile(delete=False)

        seg_filename = self._segment_to_filename(segment_name)

        if os.path.exists(seg_filename):
            with open(seg_filename) as old_segment:
                # Merge the new entries with the existing ones, so that they
                # are alphabetically sorted
                for line in old_segment:
                    word, entry = self._parse_record(line)

                    if len(entries) > 0 and word == entries[0][0]:
                        new_segment.write(
                            f"{word}:{entry}{entries[0][1]}".encode("utf-8")
                        )
                        del entries[0]

                    elif len(entries) > 0 and word > entries[0][0]:
                        new_segment.write(
                            f"{entries[0][0]}:{entries[0][1]}".encode("utf-8")
                        )
                        new_segment.write(f"{word}:{entry}".encode("utf-8"))
                        del entries[0]

                    else:
                        new_segment.write(f"{word}:{entry}".encode("utf-8"))

        # Mabye not all entries have been written so write all remaining
        # now
        while len(entries) > 0:
            new_segment.write(
                f"{entries[0][0]}:{entries[0][1]}".encode("utf-8")
            )
            del entries[0]

        # Overwrite the old segment with the new one
        new_segment.close()
        os.rename(new_segment.name, seg_filename)

    def _save_words(self):
        segments = dict()

        for word, entries in self.words.items():
            entry_text = ""
            for web_id, positions in entries.items():
                positions_text = ",".join(map(lambda p: str(p), positions))
                entry_text += f"[{web_id}|{positions_text}]"

            segment_name = self._segment_name(word)
            try:
                segments[segment_name].append((word, entry_text))
            except KeyError:
                segments[segment_name] = [(word, entry_text)]

        # TODO: rewrite with threadpool executor
        for segment_name, entries in segments.items():
            self._save_segment(segment_name, entries)

        # Clean up memory
        self.unsaved_words = 0
        self.words = dict()

    def save(
        self,
    ):
        # Save all unsaved words
        self._save_words()

        # Save all websites
        with open(self.websites_file, "w") as file:
            json.dump(self.websites, file, default=lambda o: o.__dict__)

        # Save metadata
        obj = dict()
        obj["avg_length"] = sum(
            map(lambda w: w.word_count, self.websites)
        ) / len(self.websites)
        obj["word_count"] = self.word_count
        with open(self.config_file, "w") as file:
            json.dump(obj, file)
