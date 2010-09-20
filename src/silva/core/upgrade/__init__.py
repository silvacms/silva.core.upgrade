# Copyright (c) 2009-2010 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

import ZODB.broken
import zope.security.proxy
import zope.site.hooks
import zope.site.site
import zope.app.component.hooks

def setSite(site=None):
    if site is None:
        sm = zope.component.getGlobalSiteManager()
    else:

        # We remove the security proxy because there's no way for
        # untrusted code to get at it without it being proxied again.

        # We should really look look at this again though, especially
        # once site managers do less.  There's probably no good reason why
        # they can't be proxied.  Well, except maybe for performance.

        site = zope.security.proxy.removeSecurityProxy(site)
        sm = site.getSiteManager()
        if isinstance(sm, ZODB.broken.Broken):
            # If the site manager is broken don't set it.
            return

    zope.site.hooks.siteinfo.site = site
    zope.site.hooks.siteinfo.sm = sm
    try:
        del zope.site.hooks.siteinfo.adapter_hook
    except AttributeError:
        pass

zope.site.hooks.setSite = setSite
zope.app.component.hooks.setSite = setSite

def threadSiteSubscriber(ob, event):
    setSite(ob)

zope.site.site.threadSiteSubscriber = threadSiteSubscriber


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
    'silva.core.interfaces.service IMemberService':
        'silva.core.services.interfaces IMemberService',
    'silva.core.services.interfaces ISubscriptionService':
        'silva.app.subscriptions.interfaces ISubscriptionService',
    'Products.Silva.subscriptionservice SubscriptionService':
        'silva.app.subscriptions.service SubscriptionService',

    }
