# -*- coding: utf-8 -*-
# Copyright (c) 2011 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import logging

from silva.core.interfaces import IOrderableContainer, IOrderManager
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path

logger = logging.getLogger('silva.core.upgrade')

VERSION_A1='3.0a0'

SMI_SKIN = 'silva.ui.interfaces.ISilvaUITheme'


class RootUpgrader(BaseUpgrader):

    def upgrade(self, root):
        installed_ids = root.objectIds()

        # Remove old services
        for to_remove in ['globals',
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

        # Add service filtering
        if 'service_filtering' not in installed_ids:
            factory = root.manage_addProduct['Silva']
            factory.manage_addTOCFilterService()

        # We need to install the new SilvaDocument, and Silva Obsolete
        # Document for the document migration.
        extensions = root.service_extensions
        if not extensions.is_installed('silva.app.document'):
            extensions.install('silva.app.document')
        if not extensions.is_installed('SilvaDocument'):
            extensions.install('SilvaDocument')

        # If silva.app.redirectlink we disable it (for the document
        # conversion). It can be re-enabled later on.
        if extensions.is_installed('silva.app.redirectlink'):
            extensions.uninstall('silva.app.redirectlink')

        return root


root_upgrader = RootUpgrader(VERSION_A1, 'Silva Root')


class ContainerUpgrader(BaseUpgrader):

    def validate(self, container):
        return (IOrderableContainer.providedBy(container) and
                hasattr(container, '_ordered_ids'))

    def upgrade(self, container):
        logger.info('upgrade container order %s' % content_path(container))
        manager = IOrderManager(container)
        manager.order = container._ordered_ids
        del container._ordered_ids
        return container


container_upgrader = ContainerUpgrader(VERSION_A1, AnyMetaType)
