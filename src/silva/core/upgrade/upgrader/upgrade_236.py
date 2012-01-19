# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import logging

from zope.component import getUtility
from silva.core.interfaces import IMimeTypeClassifier
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


class FileUpgrader(BaseUpgrader):
    _get_filename = None

    @property
    def get_filename(self):
        if self._get_filename is None:
            self._get_filename = getUtility(IMimeTypeClassifier).guess_filename
        return self._get_filename

    def upgrade(self, item):
        self.get_filename(item, item.getId())
        return item


file_upgrader = FileUpgrader(VERSION_SIX, 'Silva File')


class ImageUpgrader(FileUpgrader):

    def upgrade(self, item):
        for file_id in ('hires_image', 'image', 'thumbnail_image'):
            image_file = getattr(item, file_id, None)
            if image_file is None:
                continue
            self.get_filename(image_file, item.getId())
        return item

image_upgrader = ImageUpgrader(VERSION_SIX, 'Silva Image')
