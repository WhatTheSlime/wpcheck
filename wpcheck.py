#!/usr/bin/env python3
import argparse
import asyncio
import os
from tqdm.asyncio import tqdm


from h4cktools.http.httpsession import HTTPSession
from h4cktools.display import Logger
from h4cktools.parse.versions import version_regex
from h4cktools.parse.files import loadlist
from h4cktools.parse.args import urls_args, output_args, session_args

BARFORMAT = "[=] {percentage:3.0f}% |{bar}| {n_fmt}/{total_fmt}"
BARCURSOR = " =="


def parse_args():
    """Parse user arguments

    Returns:
        agrparse.NameSpace: parsed arguments    
    """
    parser = argparse.ArgumentParser(
        description="WordPress plugin version checker"
    )

    urls_args(parser)

    check = parser.add_argument_group("check arguments")
    check.add_argument(
        "slug", type=str, metavar="plugin_slug", 
        help="vulnerable plugin slug (e.g. contact-form-7)"
    )
    check.add_argument(
        "version", type=str, metavar="patched_version", 
        help="plugin patched version"
    )

    session_args(parser)
    
    output_args(parser)

    return parser.parse_args()


def get_version(response):
    """Get plugin version

    Args:
        response (h4cktools.HTTPResponse): HTTP response

    Returns:
        str: vplugin version if found, empty string otherwise
    """
    if response.code != 404:
        match = response.search(f"Stable tag: {version_regex}")
        if match:
            return match.group(1)
    return ""


async def main():
    #: Parsed Arguments
    a = parse_args()

    #: Logger object
    l = Logger(
        filename=a.output, 
        colors=not a.no_colors, 
        verbosity=a.verbosity
    )

    #: Urls to check    
    urls = []
    if a.url:
        urls = [a.url]
    if a.url_list:
        if not os.path.isfile(a.url_list):
            l.error(f"File not found: {a.url_list}")
            return
        urls = loadlist(a.url_list)

    nbt = len(urls)
    l.info(f"{nbt} hosts will be checked")
    
    #: HTTP Session object
    s = HTTPSession()

    l.info("Finding vulnerables hosts ...")
    
    futures = [
        s.get(f"{u}/wp-content/plugins/{a.slug}/readme.txt") for u in urls
    ]
    
    nbv = 0
    for f in tqdm.as_completed(futures, ascii=BARCURSOR, bar_format=BARFORMAT):
        try:
            #: HTTP Response object
            r = await f

            #: Founded version
            v = get_version(r)
            if v:
                if v < a.version:
                    l.success(
                        f"{r.host} - {a.slug} version is vulnerable: {v}"
                    )
                    nbv += 1
                else:
                    l.partial(
                        f"{r.host} - {a.slug} is not vulnerable: {v}"
                    )
            else:
                l.fail(f"{r.host} - plugin not found")
        except Exception as e:
            l.error(e)
    
    l.info(f"{nbv} hosts have vulnerable versions of {a.slug}")


if __name__ == "__main__":
    with open("logo.txt", "r") as logo:
        print(logo.read())
    asyncio.run(main())