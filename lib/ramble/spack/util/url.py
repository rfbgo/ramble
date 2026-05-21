# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

"""
Utility functions for parsing, formatting, and manipulating URLs.
"""

import re
import sys

import urllib.parse

from spack.util.path import (
    canonicalize_path,
    convert_to_platform_path,
    convert_to_posix_path,
)

is_windows = sys.platform == 'win32'


def local_file_path(url):
    """Get a local file path from a url.

    If url is a file:// URL, return the absolute path to the local
    file or directory referenced by it.  Otherwise, return None.
    """
    if isinstance(url, str):
        url = parse(url)

    if url.scheme == 'file':
        if is_windows:
            pth = convert_to_platform_path(url.netloc + url.path)
            if re.search(r'^\\[A-Za-z]:', pth):
                pth = pth.lstrip('\\')
            return pth
        return url.path

    return None


def parse(url, scheme='file'):
    """Parse a url.

    For file:// URLs, the netloc and path components are concatenated and
    passed through spack.util.path.canoncalize_path().

    Otherwise, the returned value is the same as urllib's urlparse() with
    allow_fragments=False.
    """
    # guarantee a value passed in is of proper url format. Guarantee
    # allows for easier string manipulation accross platforms
    if isinstance(url, str):
        require_url_format(url)
        url = escape_file_url(url)
    url_obj = (
        urllib.parse.urlparse(url, scheme=scheme, allow_fragments=False)
        if isinstance(url, str) else url)

    (scheme, netloc, path, params, query, _) = url_obj

    scheme = (scheme or 'file').lower()

    if scheme == 'file':

        # (The user explicitly provides the file:// scheme.)
        #   examples:
        #     file://C:\\a\\b\\c
        #     file://X:/a/b/c
        path = canonicalize_path(netloc + path)
        path = re.sub(r'^/+', '/', path)
        netloc = ''

        drive_ltr_lst = re.findall(r'[A-Za-z]:\\', path)
        is_win_path = bool(drive_ltr_lst)
        if is_windows and is_win_path:
            drive_ltr = drive_ltr_lst[0].strip('\\')
            path = re.sub(r'[\\]*' + drive_ltr, '', path)
            netloc = '/' + drive_ltr.strip('\\')

    if sys.platform == "win32":
        path = convert_to_posix_path(path)

    return urllib.parse.ParseResult(scheme=scheme,
                                    netloc=netloc,
                                    path=path,
                                    params=params,
                                    query=query,
                                    fragment=None)


def format(parsed_url):
    """Format a URL string

    Returns a canonicalized format of the given URL as a string.
    """
    if isinstance(parsed_url, str):
        parsed_url = parse(parsed_url)

    return parsed_url.geturl()


def join(base: str, *components: str, resolve_href: bool = False, **kwargs) -> str:
    """Convenience wrapper around ``urllib.parse.urljoin``, with a few differences:
    1. By default resolve_href=False, which makes the function like os.path.join: for example
    https://example.com/a/b + c/d = https://example.com/a/b/c/d. If resolve_href=True, the
    behavior is how a browser would resolve the URL: https://example.com/a/c/d.
    2. s3://, gs://, oci:// URLs are joined like http:// URLs.
    3. It accepts multiple components for convenience. Note that components[1:] are treated as
    literal path components and appended to components[0] separated by slashes."""
    # Ensure a trailing slash in the path component of the base URL to get os.path.join-like
    # behavior instead of web browser behavior.
    if not resolve_href:
        parsed = urllib.parse.urlparse(base)
        if not parsed.path.endswith("/"):
            base = parsed._replace(path=f"{parsed.path}/").geturl()
    uses_netloc = urllib.parse.uses_netloc
    uses_relative = urllib.parse.uses_relative
    try:
        # NOTE: we temporarily modify urllib internals so s3 and gs schemes are treated like http.
        # This is non-portable, and may be forward incompatible with future cpython versions.
        urllib.parse.uses_netloc = [*uses_netloc, "s3", "gs", "oci"]
        urllib.parse.uses_relative = [*uses_relative, "s3", "gs", "oci"]
        return urllib.parse.urljoin(base, "/".join(components), **kwargs)
    finally:
        urllib.parse.uses_netloc = uses_netloc
        urllib.parse.uses_relative = uses_relative


git_re = (
    r"^(?:([a-z]+)://)?"        # 1. optional scheme
    r"(?:([^@]+)@)?"            # 2. optional user
    r"([^:/~]+)?"               # 3. optional hostname
    r"(?(1)(?::([^:/]+))?|:)"   # 4. :<optional port> if scheme else :
    r"(.*[^/])/?$"              # 5. path
)


def parse_git_url(url):
    """Parse git URL into components.

    This parses URLs that look like:

    * ``https://host.com:443/path/to/repo.git``, or
    * ``git@host.com:path/to/repo.git``

    Anything not matching those patterns is likely a local
    file or invalid.

    Returned components are as follows (optional values can be ``None``):

    1. ``scheme`` (optional): git, ssh, http, https
    2. ``user`` (optional): ``git@`` for github, username for http or ssh
    3. ``hostname``: domain of server
    4. ``port`` (optional): port on server
    5. ``path``: path on the server, e.g. spack/spack

    Returns:
        (tuple): tuple containing URL components as above

    Raises ``ValueError`` for invalid URLs.
    """
    match = re.match(git_re, url)
    if not match:
        raise ValueError("bad git URL: %s" % url)

    # initial parse
    scheme, user, hostname, port, path = match.groups()

    # special handling for ~ paths (they're never absolute)
    if path.startswith("/~"):
        path = path[1:]

    if port is not None:
        try:
            port = int(port)
        except ValueError:
            raise ValueError("bad port in git url: %s" % url)

    return (scheme, user, hostname, port, path)


def require_url_format(url):
    ut = re.search(r'^(file://|http://|https://|ftp://|s3://|gs://|ssh://|git://|/)', url)
    if not ut:
        raise ValueError('Invalid url format from url: %s' % url)


def escape_file_url(url):
    drive_ltr = re.findall(r'[A-Za-z]:\\', url)
    if is_windows and drive_ltr:
        url = url.replace(drive_ltr[0], '/' + drive_ltr[0])

    return url
