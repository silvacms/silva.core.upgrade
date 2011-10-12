# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import logging

from DateTime import DateTime
from silva.core.upgrade.upgrade import BaseUpgrader, content_path
from Products.SilvaNews.AgendaItem import AgendaItemOccurrence

logger = logging.getLogger('silva.core.upgrade')

VERSION_SIX='2.3.6'


class AgendaItemVersionUpgrader(BaseUpgrader):

    def upgrade(self, item):
        logger.debug(u'update agenda item %s' % content_path(item))
        if not item.get_occurrences():
            values = {}
            for name in ['start_datetime',
                         'end_datetime',
                         'display_time',
                         'location',
                         'recurrence',
                         'all_day',
                         'timezone_name']:
                attr = '_' + name
                if attr in item.__dict__:
                    value = item.__dict__[attr]
                    if isinstance(value, DateTime):
                        value = value.asdatetime()
                    if value is not None:
                        values[name] = value
                    del item.__dict__[attr]
            item.set_occurrences([AgendaItemOccurrence(**values)])
        return item


agenda_upgrader = AgendaItemVersionUpgrader(
    VERSION_SIX, 'Silva Agenda Item Version')
