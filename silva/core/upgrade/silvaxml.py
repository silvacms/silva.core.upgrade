# Copyright (c) 2009 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import sys

NAMESPACES_CHANGES = {
    'http://infrae.com/ns/silva':
        'http://infrae.com/namespace/silva',
    'http://infrae.com/ns/silva_document':
        'http://infrae.com/namespace/silva-document',
    'http://infrae.com/namespaces/metadata/silva':
        'http://infrae.com/namespace/metadata/silva-content',
    'http://infrae.com/namespaces/metadata/silva-extra':
        'http://infrae.com/namespace/metadata/silva-extra',
    }


def upgradeNamespace(data):
    """Upgrade namespace information in a data blob.
    """
    for old, new in NAMESPACES_CHANGES.items():
        data = data.replace('"%s"' % old, '"%s"' % new)
    return data


def upgradeNamespaceOnFD(fd):
    """Upgrade namespace information on file.
    """

    fd.seek(0)
    data = fd.read()
    fd.seek(0)
    fd.write(upgradeNamespace(data))
    fd.seek(0)

