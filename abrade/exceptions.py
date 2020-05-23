"""
Exceptions for Abrade
"""

class AbradeException(Exception):
    """An error occurred while fetching or parsing data"""

class InvalidElementAttribute(AbradeException):
    """A BeautifulSoup element did not contain a requested attribute"""

class NoSuchParser(AbradeException):
    """A parser was not defined for a domain"""
