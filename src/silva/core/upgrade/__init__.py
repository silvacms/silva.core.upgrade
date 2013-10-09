# -*- coding: utf-8 -*-
# Copyright (c) 2009-2013 Infrae. All rights reserved.
# See also LICENSE.txt

CLASS_CHANGES = {
    'Products.ExtFile.ExtImage ExtImage':
        'silva.core.upgrade.upgrader.upgrade_220 ExtFile',
    'Products.ExtFile.ExtFile ExtFile':
        'silva.core.upgrade.upgrader.upgrade_220 ExtFile',
    'Products.Silva.File FileSystemFile':
        'silva.core.upgrade.upgrader.upgrade_220 SilvaFileSystemFile',
    'Products.Annotations.AnnotationTool Annotations':
        'persistent.mapping PersistentMapping',
    'Products.Silva.emaillinesfield EmailLinesField':
        'Products.Formulator.EmailLinesField EmailLinesField',
    'Products.Silva.UnicodeSplitter Splitter':
        'silva.core.services.splitter Splitter',
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
    'silva.core.interfaces.service IMemberService':
        'silva.core.services.interfaces IMemberService',
    'silva.core.services.interfaces ISubscriptionService':
        'silva.app.subscriptions.interfaces ISubscriptionService',
    'Products.Silva.subscriptionservice SubscriptionService':
        'silva.app.subscriptions.service SubscriptionService',
    'plone.keyring.interfaces IKeyManager':
        'zope.interface Interface',
    'zope.app.intid.interfaces IIntIds':
        'zope.intid.interfaces IIntIds'
    }
