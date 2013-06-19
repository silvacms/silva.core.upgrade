# -*- coding: utf-8 -*-
# Copyright (c) 2011-2012 Infrae. All rights reserved.
# See also LICENSE.txt

import logging

from zope.interface import implements

from silva.core.interfaces import IPostUpgrader
from silva.core.interfaces import IOrderableContainer, IOrderManager
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path
from Products.Silva.install import configure_metadata
from persistent.mapping import PersistentMapping


logger = logging.getLogger('silva.core.upgrade')

VERSION_A1='3.0a1'
VERSION_A2='3.0a2'

SMI_SKIN = 'silva.ui.interfaces.ISilvaUITheme'


class RootUpgrader(BaseUpgrader):

    def upgrade(self, root):
        installed_ids = root.objectIds()

        # Remove old services
        for to_remove in ['globals',
                          'service_groups',
                          'service_static_cache_manager',
                          'service_kupu',
                          'service_kupu_silva',
                          'service_renderer_registry',
                          'service_sidebar',
                          'service_typo_chars',
                          'service_view_registry',
                          'service_views',
                          'service_resources',
                          'service_views',
                          'service_toc_filter']:
            if to_remove in installed_ids:
                root.manage_delObjects([to_remove])

        # Reset SMI skin, add service_ui
        if root._smi_skin != SMI_SKIN:
            root._smi_skin = SMI_SKIN
        if 'service_ui' not in installed_ids:
            factory = root.manage_addProduct['silva.ui']
            factory.manage_addUIService()

        # Update catalog indexes
        catalog = root.service_catalog
        if 'version_status' in catalog.indexes():
            catalog.delIndex('version_status')
            catalog.addIndex('publication_status', 'FieldIndex')

        # Add service filtering
        if 'service_filtering' not in installed_ids:
            factory = root.manage_addProduct['Silva']
            factory.manage_addFilteringService()

        # If silva.app.redirectlink we disable it (for the document
        # conversion). It can be re-enabled later on.
        extensions = root.service_extensions
        if extensions.is_installed('silva.app.redirectlink'):
            extensions.uninstall('silva.app.redirectlink')

        # Update catalog indexes
        catalog = root.service_catalog
        if 'content_intid' not in catalog.schema():
            catalog.addColumn('content_intid')
        for column in ['sidebar_position', 'sidebar_title',
                       'location', 'start_datetime', 'end_datetime']:
            if column in catalog.schema():
                catalog.delColumn(column)
        for index in ['start_datetime', 'end_datetime', 'sidebar_parent',
                      'haunted_path']:
            if index in catalog.indexes():
                catalog.delIndex(index)

        configure_metadata(root.service_metadata, None)
        return root


root_upgrader = RootUpgrader(VERSION_A1, 'Silva Root')


class ContainerUpgrader(BaseUpgrader):

    def validate(self, container):
        return (IOrderableContainer.providedBy(container) and
                hasattr(container, '_ordered_ids'))

    def upgrade(self, container):
        logger.info(u'Upgrading container order in: %s.', content_path(container))
        manager = IOrderManager(container)
        get_id = manager._get_id
        order = []
        for identifier in container._ordered_ids:
            content = container._getOb(identifier, None)
            if content is not None:
                order.append(get_id(content))
        manager.order = order
        del container._ordered_ids
        return container


container_upgrader = ContainerUpgrader(VERSION_A1, AnyMetaType)


class UpdateIndexerUpgrader(BaseUpgrader):
    """Update Silva Indexer obj which uses now an id to objects and
    not the path (moving/renaming tolerant).
    """
    implements(IPostUpgrader)

    def upgrade(self, indexer):
        indexer.update()
        logger.info('Refreshed indexer %s.', content_path(indexer))
        return indexer


update_indexer_upgrader = UpdateIndexerUpgrader(VERSION_A2, 'Silva Indexer')


class UpdateHideFromTOC(BaseUpgrader):
    ns = "http://infrae.com/namespace/metadata/silva-extra"
    to_ns = "http://infrae.com/namespace/metadata/silva-settings"
    key = "hide_from_tocs"

    tags = {'pre',}

    def validate(self, content):
        annotations = getattr(content, '__annotations__', None)
        return annotations is not None and \
            self.ns in annotations and \
            self.key in annotations[self.ns]

    def upgrade(self, content):
        annotations = content.__annotations__
        from_ = annotations[self.ns]
        value = from_[self.key]
        del from_[self.key]
        to = annotations.get(self.to_ns, None)
        if to is None:
            to = annotations[self.to_ns] = PersistentMapping()
        to[self.key] = value
        logger.info("Migrated hide_from_tocs for: %s.", content_path(content))
        return content


hide_from_toc_upgrader = UpdateHideFromTOC(VERSION_A2, AnyMetaType)
