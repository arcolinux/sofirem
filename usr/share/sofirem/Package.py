"""
    This class is to encapsulate package metadata.
    It is is used inside the following:
    - Functions.userSearch()
"""


class Package(object):
    def __init__(
        self,
        name,
        description,
        category,
        subcategory,
        subcategory_description,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.subcategory = subcategory
        self.subcategory_description = subcategory_description
