# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import logging

from Products.Silva.ExtensionRegistry import extensionRegistry
from silva.core.interfaces import IContainer
from silva.core.upgrade.upgrade import BaseUpgrader, content_path


logger = logging.getLogger('silva.core.upgrade')

VERSION_FOUR='2.3.4'


def get_content_to_reindex(start):
    to_list = [start]
    folder_types = [addable_dict['name']
                    for addable_dict in extensionRegistry.get_addables()
                    if IContainer.implementedBy(addable_dict['instance'])]
    while to_list:
        content = to_list.pop(0)
        yield content
        container_ids = set(content.objectIds(folder_types))
        for publishable_id in content._ordered_ids:
            if publishable_id in container_ids:
                candidate = content._getOb(publishable_id)
                to_list.insert(0, candidate)


class SidebarUpgrader(BaseUpgrader):

    def upgrade(self, root):
        logger.debug(u'update sidebar support in root %s' % content_path(root))
        # Add missing catalog indexes and metadata
        catalog = root.service_catalog

        existing_columns = catalog.schema()
        for new_column in ['sidebar_position', 'sidebar_title']:
            if new_column not in existing_columns:
                catalog.addColumn(new_column)

        existing_indexes = catalog.indexes()
        if 'sidebar_parent' not in existing_indexes:
            catalog.addIndex('sidebar_parent', 'FieldIndex')

        logger.debug(u'reindex containers ...')
        for container in get_content_to_reindex(root):
            container.reindex_object()

        return root


sidebar_upgrader = SidebarUpgrader(VERSION_FOUR, 'Silva Root')
