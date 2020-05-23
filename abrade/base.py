"""
This module implements base Fetcher and Parser classes for Abrade

Fetcher - Handles fetching matching parsers and web requests
Parser  - Handles fetching specified properties from basic soup properties and
          getter methods
"""
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from abrade.exceptions import InvalidElementAttribute, NoSuchParser

__version__ = "0.1.1"
DEFAULT_SOUP_PARSER = "html5lib"
USER_AGENT = f"{__name__}/{__version__}"


class Parser:
    """
    Generic website parser which can populate a dictionary of properties from
    some HTML.

    A Parser object is initialised with a set of supported domains, these are
    used by Fetchers when mapping URLs to parsers.

    Properties are added to the parser using add_soup_getter() or
    add_soup_list_getter() - the former will return a single value for the
    property while the latter will return a list.

    These functions take the name of a property, followed by arguments which
    will be passed directly to BeautifulSoup's find()/find_all() methods.

    add_getter_function() allows functions to be mapped to properties for more
    complex property parsing - a BeautifulSoup object is passed to the assigned
    function when it is called.

    :param *domains: The supported domains for the parser

    Usage::

      >>> import abrade
      >>> parser = abrade.Parser()
      >>> parser.add_soup_getter("header", "h1")
      >>> parser.parse("<html><body><h1>Example</h1></body></html>")
      {"header": "Example"}
    """

    NEXT_PAGE = "__pagination_next"

    def __init__(self, *domains):
        self.supported_domains = []
        for domain in domains:
            if domain in self.supported_domains:
                continue
            self.supported_domains.append(domain)
        self.supported_properties = []
        self.soup_getters = {}
        self.soup_list_getters = {}
        self.getter_functions = {}
        self.attribute_map = {}

    def _set_internal_getters(self):
        """
        Set special internal getters to their defaults.

        These special properties apply some default logic for ease of use, but
        can be overrided like any other property.

        Currently only NEXT_PAGE is defined for use in pagination, but this
        method exists to allow further properties to be added.

        NEXT_PAGE finds an anchor tag with rel="next" by default
        """
        if self.NEXT_PAGE not in self.supported_properties:
            self.add_soup_getter(
                self.NEXT_PAGE,
                "a",
                {"rel": "next"},
                attribute="href"
            )

    @staticmethod
    def _get_element_attribute(element, attribute):
        """
        Return the specified property or attribute from a BeautifulSoup Tag
        object.

        This is a convenience method to avoid having to distinguish between
        literal attributes like .text or .contents and properties of the tag
        itself like ["href"]

        :param element: BeautifulSoup PageElement/Tag
        :param attribute: Name of the attribute or tag property to retrieve
        :return: value of attribute/tag property, or None if element is None
        :raise: ValueError if the attribute/property isn't known
        """
        if element is None:
            return None
        value = getattr(element, attribute)
        if value is not None:
            return value
        if attribute in element.attrs:
            return element[attribute]
        raise InvalidElementAttribute(
            f"attribute `{attribute}' was not found in {element}"
        )

    def parse(self, html, internal_properties=None):
        """
        Return a dictionary of supported properties and their values.

        :param html: HTML string to be parsed
        :param internal_properties: (optional)  list containing the names of any internal
            properties which should be kept in the output dictionary.
            By default, any properties with names beginning "__" are considered
            internal and are stripped from the output - any functions which
            care about those properties must specifically request for them to
            be included in output
        :return: dictionary of properties with values
        """
        self._set_internal_getters()
        soup = BeautifulSoup(html, DEFAULT_SOUP_PARSER)
        properties = {}
        for property_name in self.supported_properties:
            if property_name in self.soup_getters:
                element = soup.find(
                    *self.soup_getters[property_name]
                )
                properties[property_name] = self._get_element_attribute(
                    element,
                    self.attribute_map[property_name]
                )
            elif property_name in self.soup_list_getters:
                properties[property_name] = [
                    self._get_element_attribute(
                        element,
                        self.attribute_map[property_name]
                    )
                    for element in
                    soup.find_all(*self.soup_list_getters[property_name])
                ]
            elif property_name in self.getter_functions:
                properties[property_name] = (
                    self.getter_functions[property_name](soup)
                )
        if internal_properties is None:
            internal_properties = []
        properties = {
            k: v for k, v in properties.items()
            if k[0:2] != "__" or k in internal_properties
        }
        return properties

    def add_soup_getter(
            self,
            property_name,
            tag_name,
            tag_properties=None,
            attribute="text"
    ):
        """
        Add a property which can be retrieved by a basic BeautifulSoup find.

        :param property_name: Name of the property
        :param tag_name: Name of the HTML tag to retrieve
        :param tag_properties: (optional) Any properties the retrieved tag
            should have
        :param attribute: (optional) The attribute or property of the tag to
           retrieve. By default, the tag's .text attribute is used
        """
        self.supported_properties.append(property_name)
        if tag_properties is None:
            value = (tag_name, )
        else:
            value = (tag_name, tag_properties)
        self.soup_getters[property_name] = value
        self.attribute_map[property_name] = attribute

    def add_soup_list_getter(
            self,
            property_name,
            tag_name,
            tag_properties=None,
            attribute="text"
    ):
        """
        Add a property which will be retrieved as a list instead of a single
        value.

        :param property_name: Name of the property
        :param tag_name: Name of the HTML tag to retrieve
        :param tag_properties: (optional) Any properties the retrieved tag
            should have
        :param attribute: (optional) The attribute or property of the tag to
           retrieve. By default, the tag's .text attribute is used
        """
        if tag_properties is None:
            value = (tag_name, )
        else:
            value = (tag_name, tag_properties)
        self.supported_properties.append(property_name)
        self.soup_list_getters[property_name] = value
        self.attribute_map[property_name] = attribute

    def add_getter_function(self, property_name, function):
        """
        Add a property name to supported properties, add the function
        to getter_functions
        """
        self.supported_properties.append(property_name)
        self.getter_functions[property_name] = function


class Fetcher:
    """
    Retrieves URLs and passes their contents to a parser matching the domain.

    :param *parsers: Parsers to run against retrieved pages
    :param session: (optional) A Requests session object. Additionally allows
        the use of drop-in replacements for requests like cfscrape/cloudscraper
    """

    def __init__(self, *parsers, session=None):
        self.parsers = parsers
        if session is None:
            self.session = requests.session()
        else:
            self.session = session
        self.parser_domain_map = {}
        for parser in self.parsers:
            for domain in parser.supported_domains:
                self.parser_domain_map[domain] = parser

    def _get_parser(self, url):
        """
        Return the parser which supports the domain for the given URL.

        :param url: The URL to find a parser for
        :return: Parser object
        :raise: NoSuchParser if no parser matching the domain is found
        """
        domain = urlparse(url).hostname
        try:
            parser = self.parser_domain_map[domain]
        except KeyError:
            raise NoSuchParser(f"No parser for domain `{domain}'")
        return parser

    def fetch(self, url, **kwargs):
        """
        Fetch the page at a given URL, run a supported parser against it if
        possible and return the parser's output.

        :param url: The URL to retrieve
        """
        parser = self._get_parser(url)
        response = self.session.get(url, headers={"user-agent": USER_AGENT})
        return parser.parse(response.text, **kwargs)

    def fetch_paginated(self, url, limit=None):
        """
        Fetch the page at the given URL, and all subsequent pages.

        This uses the Parser.NEXT_PAGE property to find the URL to the next
        page. This property can be assigned a soup getter or function like any
        other.

        :param url: The starting URL to fetch
        :param limit: The maximum number of pages to fetch
        """
        parser = self._get_parser(url)
        properties = {}
        page_count = 1
        while limit is None or page_count <= limit:
            fetched_objects = self.fetch(url, internal_properties=Parser.NEXT_PAGE)
            for property_name in fetched_objects:
                if (property_name not in properties
                        or property_name not in parser.soup_list_getters):
                    properties[property_name] = fetched_objects[property_name]
                else:
                    properties[property_name].extend(
                        fetched_objects[property_name]
                    )
            if (Parser.NEXT_PAGE not in properties
                    or properties[Parser.NEXT_PAGE] is None):
                break
            if properties[Parser.NEXT_PAGE][0] == "/":
                url = urlparse(url)._replace(
                    path=properties[Parser.NEXT_PAGE]
                ).geturl()
            else:
                url = properties[Parser.NEXT_PAGE]
            page_count += 1
        properties.pop(Parser.NEXT_PAGE)
        return properties
