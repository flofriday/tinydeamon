from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import os
import json


@dataclass
class Website:
    url: str
    name: str
    description: str
    icon: str

    # TODO: check if there is a better way
    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)


class Index:
    def __init__(
        self, filename: Optional[Union[os.PathLike[Any], str, bytes]] = None
    ):
        if filename is None:
            self.websites: List[Website] = []
            self.words: Dict[str, List[int]] = dict()
            return

        with open(filename) as file:
            data = json.load(file)
            self.websites = list(map(Website.from_json, data["websites"]))
            self.words = data["words"]

    def add_website(self, website: Website, words: List[str]):
        """
        Add a website to the index.

        Runtime: O(n) with n beeing the number of words that are associated
        with the website.
        """

        index = len(self.websites)
        self.websites.append(website)

        for word in words:
            try:
                self.words[word].append(index)
            except KeyError:
                self.words[word] = [index]

    def find(self, query: str) -> List[Website]:
        """
        Find results for a query.

        Runtime: O(m*k) with m being the number of words in the query and k
        being the number of websites for the word in the query that has the
        most websites assosiated with it.
        """

        words = query.lower().split(" ")

        # Figure out which websites have all the mentioned words
        explored: Dict[int, int] = dict()
        try:
            for word in words:
                indecies = self.words[word]
                for index in indecies:
                    try:
                        explored[index] += 1
                    except KeyError:
                        explored[index] = 1
        except KeyError:
            return []

        # only return the websites wich have all the mentioned words
        websites = []
        for index, num in explored.items():
            if num >= len(words):
                websites.append(self.websites[index])

        return websites

    def save(self, filename: Union[os.PathLike[Any], str, bytes]):
        with open(filename, "w") as file:
            json.dump(
                self.__dict__, file, indent=2, default=lambda o: o.__dict__
            )
