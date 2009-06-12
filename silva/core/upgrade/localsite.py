# Copyright (c) 2008 Infrae. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.Five.site.interfaces import IFiveSiteManager
from OFS.SimpleItem import SimpleItem
from zope.app.intid.interfaces import IIntIds
from zope.app.component.interfaces import ISite
from zope.app.component.hooks import setSite
from zope.component import queryUtility
from zope.interface import alsoProvides

from five.localsitemanager import make_objectmanager_site
from five.intid.intid import OFSIntIds
from five.grok.meta import setupUtility

class IntIds(OFSIntIds, SimpleItem):
    pass


def clean_old_five_sm(context, create=True):
    """Disable the old Five sucky SM.
    """
    from Products.Five.site.localsite import disableLocalSiteHook
    std_msg = 'Please deinstall products using the local site feature.'
    disableLocalSiteHook(context)
    if not create:
        return None
    create_new_sm(context)
    return context.getSiteManager()


def create_new_sm(context):
    """Create a new SM.
    """
    make_objectmanager_site(context)
    setSite(context)


def setup_intid(context):
    """Setup intids.
    """
    service = queryUtility(IIntIds)
    if service is None:
        setupUtility(context, IntIds(), IIntds)


def activate(context):
    """Change the context to a local site.
    """
    if not ISite.providedBy(context):
        create_new_sm(context)
    sm = context.getSiteManager()
    if IFiveSiteManager.providedBy(sm):
        clean_old_five_sm(context, create=True)
    setup_intid(context)


def disable(context, interface):
    """Remove a registered utility.
    """
    sm = context.getSiteManager()
    utility = sm.queryUtility(interface)
    if IFiveSiteManager.providedBy(sm):
        parent = utility.aq_parent
        name = interface.__name__
        parent.manage_delObjects([name])
    else:
        sm.unregisterUtility(utility, interface)


