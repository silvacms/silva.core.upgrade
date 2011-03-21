# -*- coding: utf-8 -*-
# Copyright (c) 2011 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import logging


from silva.core.interfaces import IOrderableContainer, IOrderManager
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType, content_path

logger = logging.getLogger('silva.core.upgrade')

VERSION_A1='3.0a0'


class ContainerUpgrader(BaseUpgrader):

    def validate(self, container):
        return (IOrderableContainer.providedBy(container) and
                hasattr(container, '_ordered_ids'))

    def upgrade(self, container):
        logger.info('upgrade container %s' % content_path(container))
        manager = IOrderManager(container)
        manager.order = container._ordered_ids
        del container._ordered_ids
        return container


container_upgrader = ContainerUpgrader(VERSION_A1, AnyMetaType)
