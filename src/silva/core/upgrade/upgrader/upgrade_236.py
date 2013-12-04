# -*- coding: utf-8 -*-
# Copyright (c) 2002-2013 Infrae. All rights reserved.
# See also LICENSE.txt

import logging
import io

from zope.component import getUtility
from silva.core.interfaces import IMimeTypeClassifier
from silva.core.interfaces import IContainer, IGhostFolder
from silva.core.interfaces import IImage, IFile, IBlobFile
from silva.core.upgrade.upgrade import BaseUpgrader, content_path
from silva.core.interfaces.errors import UpgradeError
from silva.core.services.interfaces import ICataloging

from Products.Silva.File import BlobFile
from Products.Silva.GhostFolder.content import get_factory

logger = logging.getLogger('silva.core.upgrade')

VERSION_FINAL='2.3.6'



class ImagesUpgrader(BaseUpgrader):
    """Convert image storage to blob storage.
    """
    _guess_buffer_type = None

    @property
    def guess_buffer_type(self):
        if self._guess_buffer_type is None:
            self._guess_buffer_type = getUtility(
                IMimeTypeClassifier).guess_buffer_type
        return self._guess_buffer_type

    def upgrade_to_ghost(self, content):
        container = content.get_container()
        if not IGhostFolder.providedBy(container):
            return None
        if container.get_link_status() is not None:
            logger.warning(
                u"Invalid ghost folder invalid, not transforming: %s.",
                content_path(content))
            return None
        content_id = content.getId()
        container_haunted = container.get_haunted()
        content_haunted = container_haunted._getOb(content_id, None)
        if not IImage.providedBy(content_haunted):
            logger.warning(
                u"Original found for %s, but is not an image, not transforming it.",
                content_path(content))
            return None
        # Prevent quota system to fail if the image is an old one.
        # XXX Quota will be out of sync after the upgrade.
        if (content.hires_image is not None and
            content.hires_image.meta_type != 'Silva File'):
            content.hires_image = None
        ghost = get_factory(content_haunted)(
                    ghost=content,
                    container=container,
                    auto_delete=True,
                    auto_publish=True).modify(
            content_haunted, content_id).verify()
        logger.info(
            u"Image converted to ghost asset: %s.",
            content_path(content))
        return ghost

    def upgrade_to_file(self, content, data):
        data.seek(0)
        full_data = data.read()
        data.seek(0)
        content_type, encoding = self.guess_buffer_type(full_data)
        if content_type is None or encoding is not None:
            raise UpgradeError(u"Impossible to detect mimetype.", content)
        # Fix some bug in old Images that could be BMP
        if content.web_format not in content.web_formats:
            content.web_format = 'JPEG'
        content._image_factory('hires_image', data, content_type)
        try:
            content._create_derived_images()
        except ValueError as error:
            logger.error(error.args[0])
        data.close()
        ICataloging(content).reindex()
        logger.info(u"Image rebuilt: %s.", content_path(content))
        return content

    def upgrade(self, content):
        ghost = self.upgrade_to_ghost(content)
        if ghost is not None:
            return ghost
        # Verify stored
        data = None
        hires_image = content.hires_image
        if hires_image is None:
            hires_image = content.image
            if hires_image is None:
                # Can't do anything
                return content
        if hires_image.meta_type == 'Image':
            data = io.BytesIO(str(hires_image.data))
        elif hires_image.meta_type in ('ExtImage', 'ExtFile'):
            filename = hires_image.get_filename()
            try:
                data = open(filename, 'rb')
            except IOError:
                raise UpgradeError(u"Missing file %s." % filename, content)
        elif hires_image.meta_type == 'Silva File':
            # Already converted ?
            return content
        else:
            raise UpgradeError(u"Unknown image storage.", content)
        return self.upgrade_to_file(content, data)


image_upgrader = ImagesUpgrader(VERSION_FINAL, 'Silva Image')


class FilesUpgrader(BaseUpgrader):
    """Convert storage for a file to blob storage.
    """

    def validate(self, content):
        if IBlobFile.providedBy(content):
            return False
        return IFile.providedBy(content)

    def upgrade_to_ghost(self, content):
        container = content.get_container()
        if not IGhostFolder.providedBy(container):
            return None
        if container.get_link_status() is not None:
            logger.warning(
                u"Invalid ghost folder invalid, not transforming: %s.",
                content_path(content))
            return None
        file_id = content.getId()
        container_haunted = container.get_haunted()
        file_haunted = container_haunted._getOb(file_id, None)
        if not IFile.providedBy(file_haunted):
            logger.warning(
                u"Original found for %s, but is not an file, not transforming it.",
                content_path(content))
            return None
        ghost = get_factory(file_haunted)(
                    ghost=content,
                    container=container,
                    auto_delete=True,
                    auto_publish=True).modify(file_haunted, file_id).verify()
        logger.info(
            u"File converted to ghost asset: %s.",
            content_path(content))
        return ghost

    def upgrade(self, content):
        identifier = content.getId()
        container = content.aq_parent
        if not IContainer.providedBy(container):
            logger.error(u'Invalid file: %s', content_path(content))
            # Self-autodestruct file.
            container._delObject(identifier)
            raise StopIteration

        ghost = self.upgrade_to_ghost(content)
        if ghost is not None:
            return ghost

        new_file = BlobFile(identifier)
        tmp_identifier = identifier + 'conv_storage'
        container._setObject(tmp_identifier, new_file)
        new_file = container._getOb(tmp_identifier)
        self.replace_references(content, new_file)
        self.replace(content, new_file)
        new_file.set_file(
            content.get_file_fd(),
            content_type=content.get_content_type(),
            content_encoding=content.get_content_encoding())
        container._delObject(identifier)
        container.manage_renameObject(tmp_identifier, identifier)
        logger.info(u"File rebuilt: %s.", content_path(new_file))
        return new_file

file_upgrader = FilesUpgrader(VERSION_FINAL, 'Silva File')
