#!/usr/bin/env python
from unittest import mock, TestCase, main
import requests
from bs4 import BeautifulSoup
from abrade.base import Parser, Fetcher
from abrade.exceptions import InvalidElementAttribute, NoSuchParser

TEST_DOMAINS = ["example.com", "sub.example.com"]
TEST_URL = f"https://{TEST_DOMAINS[0]}/someplace"
TEST_PROPERTY = "test_name"
TEST_STRING = "This is a test."
TEST_TAG = "div"
TEST_TAG_PROPERTY = {"class": "test"}
TEST_A_TEXT = "example"
TEST_HTML_P1 = f"""
    <head><title>{TEST_STRING}</title></head>
    <body>
        <h1>{TEST_STRING}</h1>
        <a href="{TEST_DOMAINS[0]}">{TEST_A_TEXT}</a>
        <a class="test" href="abcd.com">further test</a>
        <div class="test">some text</div>
        <ul>
            <li>a</li>
            <li>b</li>
            <li>c</li>
            <li class="other">d</li>
            <li class="other">e</li>
        </ul>
        <a rel="next" href="https://example.com/page_two">next</a>
    </body>
"""
TEST_HTML_P2 = f"""
    <head><title>{TEST_STRING}</title></head>
    <body>
        <h1>{TEST_STRING}</h1>
        <ul>
            <li>f</li>
            <li>g</li>
            <li>h</li>
            <li class="other">i</li>
            <li class="other">j</li>
        </ul>
    </body>
"""
TEST_ATTRIBUTE = "href"


def test_getter_function(soup):
    return soup.title.text.upper()


class ParserTests(TestCase):

    def test_parser_init(self):
        parser = Parser()
        self.assertEqual(
            parser.supported_domains,
            []
        )
        self.assertEqual(
            parser.supported_properties,
            []
        )
        self.assertEqual(
            parser.soup_getters,
            {}
        )
        self.assertEqual(
            parser.soup_list_getters,
            {}
        )
        self.assertEqual(
            parser.getter_functions,
            {}
        )
        self.assertEqual(
            parser.attribute_map,
            {}
        )

    def test_parser_init_domain(self):
        parser = Parser(TEST_DOMAINS[0])
        self.assertTrue(TEST_DOMAINS[0] in parser.supported_domains)
        self.assertEqual(len(parser.supported_domains), 1)

    def test_parser_init_multi_domain(self):
        parser = Parser(TEST_DOMAINS[0], TEST_DOMAINS[1])
        self.assertTrue(
            TEST_DOMAINS[0] in parser.supported_domains
            and TEST_DOMAINS[1] in parser.supported_domains
        )
        self.assertEqual(len(parser.supported_domains), 2)

    def test_parser_init_duplicate_domain(self):
        parser = Parser(TEST_DOMAINS[0], TEST_DOMAINS[0])
        self.assertEqual(len(parser.supported_domains), 1)

    def test_set_internal_getters(self):
        parser = Parser()
        parser.parse("")
        self.assertTrue(Parser.NEXT_PAGE in parser.supported_properties)

    def test_get_element_attribute(self):
        soup = BeautifulSoup(TEST_HTML_P1, "html5lib")
        parser = Parser()
        self.assertEqual(
            parser._get_element_attribute(soup.a, "text"),
            TEST_A_TEXT
        )
        self.assertEqual(
            parser._get_element_attribute(soup.a, "href"),
            TEST_DOMAINS[0]
        )
        self.assertRaises(
            InvalidElementAttribute,
            parser._get_element_attribute,
            soup.div,
            "href"
        )

    def test_supported_properties_added(self):
        parsers = [Parser(), Parser(), Parser()]
        parsers[0].add_soup_getter(TEST_PROPERTY, TEST_TAG)
        parsers[1].add_soup_list_getter(TEST_PROPERTY, TEST_TAG)
        parsers[2].add_getter_function(TEST_PROPERTY, test_getter_function)
        for parser in parsers:
            self.assertTrue(TEST_PROPERTY in parser.supported_properties)

    def test_tag_properties_set(self):
        parser = Parser()
        parser.add_soup_getter(TEST_PROPERTY, TEST_TAG)
        self.assertTrue(parser.soup_getters[TEST_PROPERTY] == (TEST_TAG, ))
        parser.add_soup_list_getter(TEST_PROPERTY, TEST_TAG)
        self.assertTrue(
            parser.soup_list_getters[TEST_PROPERTY] == (TEST_TAG, )
        )
        parser = Parser()
        parser.add_soup_getter(
            TEST_PROPERTY,
            TEST_TAG,
            tag_properties=TEST_TAG_PROPERTY
        )
        self.assertTrue(
            parser.soup_getters[TEST_PROPERTY] == (TEST_TAG, TEST_TAG_PROPERTY)
        )
        parser.add_soup_list_getter(
            TEST_PROPERTY,
            TEST_TAG,
            tag_properties=TEST_TAG_PROPERTY
        )
        self.assertTrue(
            parser.soup_list_getters[TEST_PROPERTY]
            ==
            (TEST_TAG, TEST_TAG_PROPERTY)
        )

    def test_tag_attributes_set(self):
        parser = Parser()
        parser.add_soup_getter(TEST_PROPERTY, TEST_TAG)
        self.assertTrue(parser.attribute_map[TEST_PROPERTY] == "text")
        parser = Parser()
        parser.add_soup_getter(
            TEST_PROPERTY,
            TEST_TAG,
            attribute=TEST_ATTRIBUTE
        )
        self.assertTrue(parser.attribute_map[TEST_PROPERTY] == TEST_ATTRIBUTE)
        parser = Parser()
        parser.add_soup_list_getter(TEST_PROPERTY, TEST_TAG)
        self.assertTrue(parser.attribute_map[TEST_PROPERTY] == "text")
        parser = Parser()
        parser.add_soup_getter(
            TEST_PROPERTY,
            TEST_TAG,
            attribute=TEST_ATTRIBUTE
        )
        self.assertTrue(parser.attribute_map[TEST_PROPERTY] == TEST_ATTRIBUTE)


    def test_getter_function_added(self):
        parser = Parser()
        parser.add_getter_function(TEST_PROPERTY, test_getter_function)
        self.assertTrue(TEST_PROPERTY in parser.getter_functions)
        self.assertTrue(
            parser.getter_functions[TEST_PROPERTY] is test_getter_function
        )

    def test_add_soup_getter(self):
        parser = Parser()
        parser.add_soup_getter(TEST_PROPERTY, TEST_TAG)
        self.assertTrue(TEST_PROPERTY in parser.supported_properties)
        self.assertTrue(
            parser.soup_getters[TEST_PROPERTY] == (TEST_TAG, )
        )
        parser = Parser()
        parser.add_soup_getter(
            TEST_PROPERTY,
            TEST_TAG,
            TEST_TAG_PROPERTY
        )
        self.assertTrue(TEST_PROPERTY in parser.supported_properties)
        self.assertTrue(
            parser.soup_getters[TEST_PROPERTY] == (TEST_TAG, TEST_TAG_PROPERTY)
        )

    def test_parse(self):
        parser = Parser()
        parser.add_soup_getter("header", "h1")
        parser.add_soup_getter("with_property", "div", {"class": "test"})
        parser.add_soup_list_getter("lis", "li")
        parser.add_soup_list_getter("lis_others", "li", {"class": "other"})
        parser.add_getter_function("function", test_getter_function)
        parser.add_soup_getter("a_href", "a", attribute="href")
        parser.add_soup_getter("a_text", "a", attribute="text")
        result = parser.parse(TEST_HTML_P1)
        self.assertEqual(
            result,
            {
                "header": TEST_STRING,
                "with_property": "some text",
                "lis": ["a", "b", "c", "d", "e"],
                "lis_others": ["d", "e"],
                "function": TEST_STRING.upper(),
                "a_href": TEST_DOMAINS[0],
                "a_text": TEST_A_TEXT,
            }
        )


class FetcherTests(TestCase):

    def test_fetcher_init(self):
        fetcher = Fetcher()
        self.assertEqual(fetcher.parsers, ())
        self.assertIsInstance(fetcher.session, requests.Session)
        parser = Parser()
        session = requests.session()
        fetcher = Fetcher(parser, session=session)
        self.assertTrue(parser in fetcher.parsers)
        self.assertTrue(fetcher.session is session)

    def test_get_parser(self):
        parser = Parser(TEST_DOMAINS[0])
        fetcher = Fetcher(parser)
        self.assertTrue(parser is fetcher._get_parser(TEST_URL))
        self.assertRaises(
            NoSuchParser,
            fetcher.fetch,
            TEST_DOMAINS[1]
        )

    def test_fetch_end_result(self):
        parser = Parser(TEST_DOMAINS[0])
        parser.add_soup_getter("header", "h1")
        parser.add_soup_getter("with_property", "div", {"class": "test"})
        parser.add_soup_list_getter("lis", "li")
        parser.add_soup_list_getter("lis_others", "li", {"class": "other"})
        parser.add_getter_function("function", test_getter_function)
        parser.add_soup_getter("a_href", "a", attribute="href")
        parser.add_soup_getter("a_text", "a", attribute="text")
        response = mock.Mock()
        response.text = TEST_HTML_P1
        session = requests.session()
        session.get = mock.Mock(return_value=response)
        fetcher = Fetcher(parser, session=session)
        result = fetcher.fetch(TEST_URL)
        self.assertEqual(
            result,
            {
                "header": TEST_STRING,
                "with_property": "some text",
                "lis": ["a", "b", "c", "d", "e"],
                "lis_others": ["d", "e"],
                "function": TEST_STRING.upper(),
                "a_href": TEST_DOMAINS[0],
                "a_text": TEST_A_TEXT,
            }
        )

    def test_fetch_paginated(self):
        def return_page(url, *args, **kwargs):
            response = mock.Mock()
            if url == "https://example.com/page_two":
                response.text = TEST_HTML_P2
            else:
                response.text = TEST_HTML_P1
            return response
        session = mock.Mock()
        session.get = return_page
        parser = Parser(TEST_DOMAINS[0])
        parser.add_soup_getter("header", "h1")
        parser.add_soup_list_getter("lis", "li")
        fetcher = Fetcher(parser, session=session)
        result = fetcher.fetch_paginated(TEST_URL)
        self.assertEqual(
            result,
            {
                "header": TEST_STRING,
                "lis": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
            }
        )


if __name__ == "__main__":
    main()
