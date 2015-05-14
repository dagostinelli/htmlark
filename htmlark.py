#!/usr/bin/env python3

# Pack a webpage including images and CSS into a single HTML file.

import argparse
import requests
import base64
from urllib.parse import urlparse, urljoin
import mimetypes
from bs4 import BeautifulSoup

#TODO: Ignore files already data-URI encoded
#TODO: Read/write from/to stdin/stdout

def get_options():
    """Parses command line options"""
    parser = argparse.ArgumentParser(description="Converts a webpage including external resources into a single HTML file")
    parser.add_argument('webpage', help="URL or path of webpage to convert")
    parser.add_argument('--ignore-images', action='store_true', default=False,
                        help="Ignores images during conversion")
    parser.add_argument('--ignore-css', action='store_true', default=False,
                        help="Ignores stylesheets during conversion")
    parser.add_argument('--ignore-js', action='store_true', default=False,
                        help="Ignores Javascript during conversion")
    #TODO: Check for lxml/html5lib availability, use by default if exists
    parser.add_argument('-p', '--parser', default='html.parser',
                        choices=['html.parser', 'lxml', 'html5lib'],
                        help="Select HTML parser. See manual for details.")
    return parser.parse_args()

def make_data_uri(mimetype, data):
    """
    Converts data into a base64-encoded data URI.

    Arguments:
    mimetype - String containing the MIME type of data (e.g. image/jpeg). If
        None, will be treated as an empty string.
    data - Raw data to be encoded.
    """
    mimetype = '' if mimetype == None else mimetype
    encoded_data = base64.b64encode(data).decode()
    return "data:{};base64,{}".format(mimetype, encoded_data)

def get_resource(resource_url):
    """
    Downloads or reads a file (online or local)

    Arguments:
    resource_url - URL or path of resource to load
    mode - Returns text string if 'r', or bytes if 'rb'
    """
    url_parsed = urlparse(resource_url)
    if url_parsed.scheme in ['http', 'https']:
        request = requests.get(resource_url)
        data = request.content
        if 'Content-Type' in request.headers:
            mimetype = request.headers['Content-Type']
        else:
            mimetype = mimetypes.guess_type(resource_url)
    elif url_parsed.scheme == '':
        # '' is local file
        data = open(resource_url, 'rb').read()
        mimetype, _ = mimetypes.guess_type(resource_url)
    elif url_parsed.scheme == 'data':
        raise ValueError("Resource path is a data URI")
    else:
        raise ValueError("Not local path or HTTP/HTTPS URL")

    return data, mimetype

def convert_page(page_path, parser, callback=lambda *_:None,
                 ignore_images=False, ignore_css=False, ignore_js=False):
    """
    Takes an HTML file or URL and outputs new HTML with resources as data URIs.

    Arguments:
    pageurl - URL or path of web page to convert.
    parser - Parser for Beautiful Soup 4 to use. See BS4's docs for more info.
    ignore_images - If true do not process <img> tags
    ignore_css - If true do not process <link> (stylesheet) tags
    ignore_js - If true do not process <script> tags
    callback - Called before a new resource is processed. Takes a BS4 tag
        object as a parameter.

    Returns: String containing the new webpage HTML.
    """

    # Get page HTML, whether from a server or a local file
    page_text, _ = get_resource(page_path)

    # Not all parsers are equal - if one skips resources, try another
    soup = BeautifulSoup(page_text, parser)
    tags = []

    # Gather all the relevant tags together
    if not ignore_images:
        tags += soup('img')
    if not ignore_css:
        csstags = soup('link')
        for css in csstags:
            if 'stylesheet' in css['rel']:
                tags.append(css)
    if not ignore_js:
        scripttags = soup('script')
        for script in scripttags:
            if 'src' in script.attrs:
                tags.append(script)

    # Convert the linked resources
    for tag in tags:
        tag_url = tag['href'] if tag.name == 'link' else tag['src']
        tag_data, tag_mime = get_resource(urljoin(page_path, tag_url))
        encoded_resource = make_data_uri(tag_mime, tag_data)
        if tag.name == 'link':
            tag['href'] = encoded_resource
        else:
            tag['src'] = encoded_resource
        callback(tag.name, tag_url)

    return str(soup)

def main():
    """Script's main function, used when called as a command-line program"""

    options = get_options()

    print("Processing {}".format(options.webpage))

    def info_callback(tag_name, tag_url):
        """Displays progress information during conversion"""
        if tag_name == 'img':
            tagtype = "Image"
        elif tag_name == 'link':
            tagtype = "CSS"
        elif tag_name == 'script':
            tagtype = "JS"
        else:
            tagtype = tag_name
        print("{}: {}".format(tagtype, tag_url))

    newhtml = convert_page(options.webpage, options.parser,
                           ignore_images=options.ignore_images,
                           ignore_css=options.ignore_css,
                           ignore_js=options.ignore_js,
                           callback=info_callback)

    outfile = open('out.html', 'w')
    outfile.write(newhtml)
    outfile.close()
    print("All done, file written to " + "out.html")

if __name__ == "__main__":
    main()
