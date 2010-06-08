# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$


CLASS_CHANGES = {
    'Products.Annotations.AnnotationTool Annotations':
        'persistent.mapping PersistentMapping',
    'Products.Silva.interfaces IInvisibleService':
        'silva.core.interfaces.service IInvisibleService',
    'Products.Silva.interfaces.service IInvisibleService':
        'silva.core.interfaces.service IInvisibleService',
    'Products.SilvaMetadata.interfaces ICatalogService':
        'silva.core.services.interfaces ICatalogService',
    'Products.SilvaMetadata.CatalogTool CatalogService':
        'silva.core.services.catalog CatalogService',
    'Products.XMLWidgets.WidgetRegistry WidgetRegistry':
        'OFS.SimpleItem SimpleItem',
    'Products.SilvaReferenceCheckerSupport.install IExtension':
        'zope.interface Interface',
    'silva.core.layout IExtension':
        'zope.interface Interface',
    'silva.core.upgrade.localsite IntIds':
        'silva.core.services.base IntIdService',
    }

