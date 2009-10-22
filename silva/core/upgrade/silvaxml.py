# Copyright (c) 2009 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import sys
import cStringIO

NAMESPACES_CHANGES = {
    'http://infrae.com/ns/silva':
        'http://infrae.com/namespace/silva',
    'http://infrae.com/ns/silva_document':
        'http://infrae.com/namespace/silva-document',
    'http://infrae.com/namespaces/metadata/silva':
        'http://infrae.com/namespace/metadata/silva-content',
    'http://infrae.com/namespaces/metadata/silva-extra':
        'http://infrae.com/namespace/metadata/silva-extra',
    'http://infrae.com/namespaces/metadata/silva-layout':
        'http://infrae.com/namespace/metadata/silva-layout',
    'http://infrae.com/ns/silva-news-network':
        'http://infrae.com/namespace/silva-news-network',
    'http://infrae.com/namespaces/metadata/snn-np-settings':
        'http://infrae.com/namespace/metadata/snn-np-settings',
    }


def upgradeNamespace(data):
    """Upgrade namespace information in a data blob.
    """
    for old, new in NAMESPACES_CHANGES.items():
        data = data.replace('"%s"' % old, '"%s"' % new)
    return data


def upgradeXMLOnFD(fd):
    """Upgrade namespace information on file.
    """

    fd.seek(0)
    data = fd.read()
    new_fd = cStringIO.StringIO()
    new_fd.write(upgradeNamespace(data))
    new_fd.seek(0)
    return new_fd

