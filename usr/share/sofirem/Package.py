# This class is to encapsulate package metadata, taken from the yaml files stored inside the sofirem github repository


class Package(object):
    def __init__(
        self,
        name,
        description,
        category,
        subcategory,
        subcategory_description,
        version,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.subcategory = subcategory
        self.subcategory_description = subcategory_description
        self.version = version
