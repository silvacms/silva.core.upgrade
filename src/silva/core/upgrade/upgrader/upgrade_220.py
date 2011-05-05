# Copyright (c) 2002-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from cStringIO import StringIO
import logging

logger = logging.getLogger('silva.core.upgrade')

from ZPublisher.BeforeTraverse import unregisterBeforeTraverse
from zope.annotation.interfaces import IAnnotations
from zope.app.component.hooks import setSite, setHooks
from zope.location.interfaces import ISite
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

from Products.Silva.adapters import version_management
from Products.Silva.File import BlobFile
from Products.Silva.magic import MagicGuess
from Products.SilvaExternalSources.interfaces import ICodeSourceService
from Products.SilvaMetadata.interfaces import IMetadataService


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

        reg = obj.service_view_registry
        reg.unregister('public', 'Silva Document Version')
        reg.unregister('add', 'Silva Document')
        reg.unregister('preview', 'Silva Document Version')

        # Delete unused Silva views
        reg.unregister('public', 'Silva AutoTOC')

        # Clean SilvaLayout mess
        if hasattr(obj, "__silva_layout_installed__"):
            # XXX fix this
            # if 'silva-layout-vhost-root' in obj.service_metadata.getCollection().getMetadataSets():
            #     resetMetadata(obj, ['silva-layout-vhost-root'])
            reg.unregister('edit', 'Silva Layout Configuration')
            reg.unregister('public', 'Silva Layout Configuration')
            reg.unregister('add', 'Silva Layout Configuration')
            if hasattr(obj.service_views, 'SilvaLayout'):
                obj.service_views.manage_delObjects(['SilvaLayout'])
            # update the views (in service_view_registry) to ensure
            # that SilvaLayout is removed from it's internal list
            # of root view directories
            obj.service_extensions._update_views(obj)

        # Update service_files settings
        service_files = obj.service_files
        if hasattr(service_files, '_filesystem_storage_enabled'):
            if service_files._filesystem_storage_enabled:
                service_files.storage = BlobFile
            delattr(service_files , '_filesystem_storage_enabled')

        return obj


root_upgrader = RootUpgrader(VERSION_A1, 'Silva Root')


class ImagesUpgrader(BaseUpgrader):

    magic_guess = MagicGuess()

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
        ct = self.magic_guess.buffer(full_data)
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


class SilvaXMLUpgrader(BaseUpgrader):
    '''Upgrades all SilvaXML (documents), converting
       <toc> elements to cs_toc sources and
       <citation> elements to cs_citation sources'''
    def upgrade(self, obj):
        if interfaces.IVersionedContent.providedBy(obj):
            vm = version_management.getVersionManagementAdapter(obj)
            for version in vm.getVersions():
                if hasattr(version, 'content'):
                    dom = version.content
                    if hasattr(dom, 'documentElement'):
                        self._upgrade_tocs(version, dom.documentElement)
                        self._upgrade_citations(version, dom.documentElement)
        return obj

    def _upgrade_citations(self, version, doc_el):
        cites = doc_el.getElementsByTagName('cite')
        if cites:
            logger.info('upgrading CITE Elements in: %s' % (
                '/'.join(version.getPhysicalPath())))
        else:
            return

        for c in cites:
            author = source = ''
            citation = []
            #html isn't currently allowed in author, source, so
            # we don't need to "sanity" check them!
            for node in c.childNodes:
                if not node.firstChild:
                    continue
                val = node.firstChild.\
                    writeStream().getvalue().replace('&lt;','<')
                if node.nodeType == node.ELEMENT_NODE:
                    if node.nodeName == 'author':
                        author = val
                    elif node.nodeName == 'source':
                        source = val
                    else:
                        citation.append(val)
                else:
                    citation.append(val)
            citation = ''.join(citation)

            cs = doc_el.createElement('source')
            cs.setAttribute('id','cs_citation')

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','source')
            p.appendChild(doc_el.createTextNode(source))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','author')
            p.appendChild(doc_el.createTextNode(author))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','citation')
            p.appendChild(doc_el.createTextNode(citation))
            cs.appendChild(p)

            c.parentNode.replaceChild(cs,c)

    def _upgrade_tocs(self, version, doc_el):
        tocs = doc_el.getElementsByTagName('toc')
        if tocs:
            logger.info('upgrading TOC Elements in: %s' %
                        ('/'.join(version.getPhysicalPath())))
        else:
            return
        path = '/'.join(version.get_container().getPhysicalPath())
        for t in tocs:
            depth = t.getAttribute('toc_depth')
            if not depth:
                depth = '0'

            cs = doc_el.createElement('source')
            cs.setAttribute('id','cs_toc')

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','paths')
            p.appendChild(doc_el.createTextNode(path))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','boolean')
            p.setAttribute('key','show_icon')
            p.appendChild(doc_el.createTextNode('0'))
            cs.appendChild(p)

            #don't add this parameter, instead let silva
            # use the default value, which is to show
            # all publishable types
            #p = doc_el.createElement('parameter')
            #p.setAttribute('type','list')
            #p.setAttribute('key','toc_types')
            #toc_types = tocrendering.compute_default_show_types()
            #s = str(toc_types)
            #p.appendChild(doc_el.createTextNode(str(toc_types))
            #"['Silva Document','Silva Folder','Silva Publication']"))
            #cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','css_class')
            cs.appendChild(p)

            # make sure the sort order is the old default, of 
            # "silva folder order"
            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','sort_on')
            p.appendChild(doc_el.createTextNode('silva'))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','capsule_title')
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','depth')
            p.appendChild(doc_el.createTextNode(depth))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','boolean')
            p.setAttribute('key','display_headings')
            p.appendChild(doc_el.createTextNode('0'))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','alignment')
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','css_style')
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','string')
            p.setAttribute('key','order')
            p.appendChild(doc_el.createTextNode('normal'))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','boolean')
            p.setAttribute('key','link_headings')
            p.appendChild(doc_el.createTextNode('0'))
            cs.appendChild(p)

            p = doc_el.createElement('parameter')
            p.setAttribute('type','boolean')
            p.setAttribute('key','show_desc')
            p.appendChild(doc_el.createTextNode('0'))
            cs.appendChild(p)

            t.parentNode.replaceChild(cs,t)

silva_xml_ugrader = SilvaXMLUpgrader(VERSION_A2, AnyMetaType)


class AllowedAddablesUpgrader(BaseUpgrader):

    def upgrade(self, obj):
        if interfaces.IContainer.providedBy(obj):
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


update_indexer_upgrader = UpdateIndexerUpgrader(VERSION_B1, 'Silva Indexer')


class SecondRootUpgrader(BaseUpgrader):
    """Change standard_error_message to default_standard_error_message.
    """

    def upgrade(self, obj):
        # Update the error message handling
        if obj.__dict__.has_key('standard_error_message'):
            obj._setObject(
                'default_standard_error_message',
                obj.__dict__['standard_error_message'])
            obj._delObject('standard_error_message')

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

        reg = obj.service_view_registry
        reg.unregister('public', 'Silva Document')
        reg.unregister('public', 'Silva Link')
        reg.unregister('public', 'Silva Find')
        reg.unregister('preview', 'Silva Find')
        reg.unregister('add', 'Silva Find')

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
        # Setup SilvaLayout
        if not service_ext.is_installed('SilvaLayout'):
            try:
                import Products.SilvaLayout
            except ImportError:
                logger.info('Products.SilvaLayout is not installed, '
                            'skipping installation of extension')
            else:
              service_ext.install('SilvaLayout')

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

                new_annotations[key] = new_data

            # remove old annotations
            del aq_base(obj)._portal_annotations_
        return obj


metadata_upgrader = MetadataUpgrader(VERSION_B1, AnyMetaType)
