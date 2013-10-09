# -*- coding: utf-8 -*-
# Copyright (c) 2002-2013 Infrae. All rights reserved.
# See also LICENSE.txt

import logging

from zope.component import getUtility
from silva.core.interfaces import IMimeTypeClassifier
from silva.core.upgrade.upgrade import BaseUpgrader, content_path

logger = logging.getLogger('silva.core.upgrade')

VERSION_SIX='2.3.6'


class FileUpgrader(BaseUpgrader):
    _update_filename = None

    tags = {'pre',}

    @property
    def update_filename(self):
        if self._update_filename is None:
            self._update_filename = getUtility(
                IMimeTypeClassifier).guess_filename
        return self._update_filename

    def upgrade(self, item):
        old_filename = item.get_filename()
        new_filename = self.update_filename(item, item.getId())
        if old_filename != new_filename:
            logger.debug('update filename from %s to %s (%s), in %s' % (
                    old_filename, new_filename,
                    item.content_type(), content_path(item)))
        return item

# Those should be correctly generated in upgrade_220 now.
#file_upgrader = FileUpgrader(VERSION_SIX, 'Silva File')


class ImageUpgrader(FileUpgrader):

    tags = {'pre',}

    def upgrade(self, item):
        for file_id in ('hires_image', 'image', 'thumbnail_image'):
            item_file = getattr(item, file_id, None)
            if item_file is None:
                continue
            old_filename = item_file.get_filename()
            new_filename = self.update_filename(item_file, item.getId())
            if old_filename != new_filename:
                logger.debug('update filename from %s to %s (%s), in %s' % (
                        old_filename, new_filename,
                        item_file.content_type(), content_path(item)))
        return item

# Those should be correctly generated in upgrade_220 now.
#image_upgrader = ImageUpgrader(VERSION_SIX, 'Silva Image')
