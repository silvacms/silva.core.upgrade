# Copyright (c) 2008 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.Five.site.interfaces import IFiveSiteManager
from zope.app.component.interfaces import ISite
from zope.app.component.hooks import setSite
from zope.component import queryUtility

from five.localsitemanager import make_objectmanager_site


def clean_old_five_sm(context, create=True):
    """Disable the old Five sucky SM.
    """
    from Products.Five.site.localsite import disableLocalSiteHook
    std_msg = 'Please deinstall products using the local site feature.'
    if list(sm.registeredAdapters()):
        raise ValueError, 'Still have registered adapters. ' + std_msg
    if list(sm.registeredUtilities()):
        raise ValueError, 'Still have registered utilities. ' + std_msg
    disableLocalSiteHook(context)
    if not create:
        return None
    make_objectmanager_site(context)
    setSite(context)
    return context.getSiteManager()


def activate(context):
    """Change the context to a local site.
    """
    if not ISite.providedBy(context):
        make_objectmanager_site(context)
        setSite(context)
    sm = context.getSiteManager()
    if IFiveSiteManager.providedBy(sm):
        clean_old_five_sm(context, create=True)


def disable(context, interface):
    """Remove a registered utility.
    """
    sm = context.getSiteManager()
    utility = sm.queryUtility(interface)
    if IFiveSiteManager.providedBy(sm):
        parent = utility.aq_parent
        name = interface.__class__.__name__.split('.')[-1]
        parent.manage_delObjects([name])
    else:
        sm.unregisterUtility(utility, interface)


