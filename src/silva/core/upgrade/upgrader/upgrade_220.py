# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from cStringIO import StringIO
import logging

from ZPublisher.BeforeTraverse import unregisterBeforeTraverse
from zope.annotation.interfaces import IAnnotations
from zope.site.hooks import setSite, setHooks
from zope.location.interfaces import ISite
from zope.component import getUtility
import ZODB.broken
import zope.interface

try:
    # Old FiveSiteManager. This have been removed in Zope 2.12.
    from Products.Five.site.interfaces import IFiveSiteManager
except ImportError:
    IFiveSiteManager = None

from Acquisition import aq_base

from silva.core import interfaces
from silva.core.services.catalog import CatalogService
from silva.core.services.interfaces import ICatalogService
from silva.core.upgrade.localsite import setup_intid
from silva.core.upgrade.silvaxml import NAMESPACES_CHANGES
from silva.core.upgrade.upgrade import BaseUpgrader, AnyMetaType

from Products.Silva.File import BlobFile
from Products.SilvaExternalSources.interfaces import ICodeSourceService
from Products.SilvaMetadata.interfaces import IMetadataService

logger = logging.getLogger('silva.core.upgrade')


#-----------------------------------------------------------------------------
# 2.1.0 to 2.2.0a1
#-----------------------------------------------------------------------------

VERSION_A1='2.2a1'


class RootUpgrader(BaseUpgrader):

    def upgrade(self, obj):
        # If it's a Five site manager disable it first. The annoying
        # part might be that the code might already have been removed
        # from Zope ...
        if ISite.providedBy(obj):
            sm = obj.getSiteManager()
            if ((IFiveSiteManager is not None and
                 IFiveSiteManager.providedBy(sm)) or
                isinstance(sm, ZODB.broken.Broken)):
                setSite(None)
                setHooks()
                unregisterBeforeTraverse(aq_base(obj), '__local_site_hook__')
                if hasattr(aq_base(obj), '__local_site_hook__'):
                    delattr(aq_base(obj), '__local_site_hook__')
                zope.interface.noLongerProvides(obj, ISite)
                obj.setSiteManager(None)

        # Activate local site, add an intid service.
        ism = interfaces.ISiteManager(obj)
        if not ism.isSite():
            ism.makeSite()
        setSite(obj)
        setHooks()

        # Delete unused Silva Document service
        for s in ['service_doc_previewer',
                  'service_nlist_previewer',
                  'service_sub_previewer',]:
            if hasattr(obj, s):
                obj.manage_delObjects([s,])

        # Update service_files settings
        service_files = obj.service_files
        if hasattr(service_files, '_filesystem_storage_enabled'):
            if service_files._filesystem_storage_enabled:
                service_files.storage = BlobFile
            delattr(service_files , '_filesystem_storage_enabled')

        return obj


root_upgrader = RootUpgrader(VERSION_A1, 'Silva Root')


class ImagesUpgrader(BaseUpgrader):
    _guess_buffer_type = None

    @property
    def guess_buffer_type(self):
        if self._guess_buffer_type is None:
            self._guess_buffer_type = getUtility(
                interfaces.IMimeTypeClassifier).guess_buffer_type
        return self._guess_buffer_type

    def upgrade(self, obj):
        # Add stuff here
        data = None
        hires_image = obj.hires_image
        if hires_image is None:
            hires_image = obj.image
        if hires_image is None:
            # Can't do anything
            return obj
        if hires_image.meta_type == 'Image':
            data = StringIO(str(hires_image.data))
        elif hires_image.meta_type == 'ExtImage':
            filename = hires_image.get_filename()
            try:
                data = open(filename, 'rb')
            except IOError:
                raise ValueError, "Missing file %s" % filename
        elif hires_image.meta_type == 'Silva File':
            # Already converted ?
            return obj
        else:
            raise ValueError, "Unknown mimetype"
        data.seek(0)
        full_data = data.read()
        data.seek(0)
        ct = self.guess_buffer_type(full_data)
        if not ct:
            raise ValueError, "Impossible to detect mimetype"
        # fix some bug in old Images that could be BMP
        if obj.web_format not in obj.web_formats:
            obj.web_format = 'JPEG'
        obj._image_factory('hires_image', data, ct)
        obj._createDerivedImages()
        data.close()
        logger.info("image %s rebuilt" % '/'.join(obj.getPhysicalPath()))
        return obj


images_upgrader = ImagesUpgrader(VERSION_A1, 'Silva Image')


#-----------------------------------------------------------------------------
# 2.2.0a1 to 2.2.0a2
#-----------------------------------------------------------------------------


VERSION_A2='2.2a2'


class AllowedAddablesUpgrader(BaseUpgrader):

    def validate(self, obj):
        return interfaces.IContainer.providedBy(obj)

    def upgrade(self, obj):
        clean_obj = aq_base(obj)
        if hasattr(clean_obj,'_addables_allowed_in_publication'):
            clean_obj._addables_allowed_in_container = \
                clean_obj._addables_allowed_in_publication
            del clean_obj._addables_allowed_in_publication
        elif not hasattr(clean_obj, '_addables_allowed_in_container'):
            clean_obj._addables_allowed_in_container = None
        return obj


allowed_addables_upgrader = AllowedAddablesUpgrader(VERSION_A2, AnyMetaType)

#-----------------------------------------------------------------------------
# 2.2.0a2 to 2.2.0b1
#-----------------------------------------------------------------------------

VERSION_B1='2.2b1'


class UpdateIndexerUpgrader(BaseUpgrader):
    """Update Silva Indexer obj which uses now an id to objects and
    not the path (moving/renaming tolerant).
    """

    def upgrade(self, obj):
        obj.update()
        logger.info('refresh indexer %s' % (
                '/'.join(obj.getPhysicalPath())))
        return obj


#update_indexer_upgrader = UpdateIndexerUpgrader(VERSION_B1, 'Silva Indexer')


class SecondRootUpgrader(BaseUpgrader):
    """Change standard_error_message to default_standard_error_message.
    """

    def upgrade(self, obj):
        # Register service_files and others
        sm = obj.getSiteManager()
        sm.registerUtility(obj.service_files, interfaces.IFilesService)
        if hasattr(obj, 'service_codesources'):
            # We should have it however ...
            sm.registerUtility(obj.service_codesources, ICodeSourceService)

        # Update metadata service
        metadata = obj.service_metadata
        sm.registerUtility(metadata, IMetadataService)

        # Update the catalog
        setup_intid(obj)
        catalog = obj.service_catalog
        catalog.__class__ = CatalogService
        sm.registerUtility(catalog, ICatalogService)
        indexes = catalog._catalog.indexes
        for key, index in indexes.items():
            if index.__class__.__name__ == 'ProxyIndex':
                del indexes[key]
        catalog._catalog.indexes = indexes
        # We reinitialize the metadata sets to recreate indexes
        for mset in metadata.collection.objectValues():
            for melt in mset.objectValues():
                if ('doc_attr' in melt.index_constructor_args and
                    melt.index_constructor_args['doc_attr'] == 'proxy_value'):
                    del melt.index_constructor_args['doc_attr']
                if melt.index_type == 'TextIndex':
                    melt.index_type = 'ZCTextIndex'
                    melt.index_constructor_args.update(
                        {'index_type': 'Cosine Measure',
                         'lexicon_id': 'silva_lexicon'})
            mset.initialized = 0
            mset.initialize()

        if hasattr(obj, 'service_annotations'):
            obj.manage_delObjects(['service_annotations'])

        # Setup the cs_toc and cs_citation CS's.
        service_ext = obj.service_extensions
        if not service_ext.is_installed('SilvaExternalSources'):
            service_ext.install('SilvaExternalSources')
        else:
            service_ext.refresh('SilvaExternalSources')
        if not hasattr(obj, 'cs_toc'):
            toc = obj.service_codesources.manage_copyObjects(['cs_toc',])
            obj.manage_pasteObjects(toc)
        if not hasattr(obj, 'cs_citation'):
            cit = obj.service_codesources.manage_copyObjects(['cs_citation',])
            obj.manage_pasteObjects(cit)

        return obj

second_root_upgrader = SecondRootUpgrader(VERSION_B1, 'Silva Root', 50)


class MetadataSetUpgrader(BaseUpgrader):
    """Update the namespaces of existing metadata sets NOTE: this
    'may' not be needed, since I think the metadata sets _are_
    reinstalled during the refresh, but we do it here for good measure.
    """

    def upgrade(self, obj):
        sm = obj.service_metadata
        sets = sm.getCollection().getMetadataSets()
        for s in sets:
            prefix,uri = s.getNamespace()
            if NAMESPACES_CHANGES.has_key(uri):
                s.setNamespace(NAMESPACES_CHANGES[uri], prefix)
        return obj


metadata_set_upgrader = MetadataSetUpgrader(VERSION_B1, 'Silva Root', 40)


class MetadataUpgrader(BaseUpgrader):
    """Migrate metadata information.
    """

    def upgrade(self, obj):
        if not (interfaces.ISilvaObject.providedBy(obj) or
                interfaces.IVersion.providedBy(obj)):
            return obj
        old_annotations = getattr(aq_base(obj), '_portal_annotations_', None)
        if old_annotations is not None:
            logger.info('upgrading metadata for %s' % (
                    '/'.join(obj.getPhysicalPath())))
            new_annotations = IAnnotations(aq_base(obj))

            for key in old_annotations.keys():
                old_data = old_annotations[key]
                # if it is metadata, we have to update the namespaces
                # as well inside the data, they will go directly in
                # the annotation
                if key == 'http://www.infrae.com/xml/metadata':
                    for old_key in old_data.keys():
                        if old_key in NAMESPACES_CHANGES:
                            new_key = NAMESPACES_CHANGES[old_key]
                        else:
                            new_key = old_key
                        new_annotations[new_key] = old_data[old_key]
                    continue

                #new_annotations[key] = new_data

            # remove old annotations
            del aq_base(obj)._portal_annotations_
        return obj


metadata_upgrader = MetadataUpgrader(VERSION_B1, AnyMetaType)
