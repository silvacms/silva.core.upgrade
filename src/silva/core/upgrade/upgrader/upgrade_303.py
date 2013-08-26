from silva.core.upgrade.upgrade import BaseUpgrader
from silva.core.editor.utils import DEFAULT_PER_TAG_WHITELISTS
from silva.core.editor.utils import DEFAULT_HTML_ATTR_WHITELIST
from silva.core.editor.utils import DEFAULT_CSS_PROP_WHITELIST


VERSION = '3.0.3'


class CKEditorServiceUpgrader(BaseUpgrader):
    """Upgrade a pre-existing Sanitizer configuration object.
    """

    def upgrade(self, service):
        if '_per_tag_allowed_attr' not in service.__dict__:
            service.__dict__['_per_tag_allowed_attr'] = set(
                DEFAULT_PER_TAG_WHITELISTS)
        if '_allowed_html_tags' in service.__dict__:
            del service.__dict__['_allowed_html_tags']
        service._allowed_html_attributes = set(DEFAULT_HTML_ATTR_WHITELIST)
        service._allowed_css_attributes = set(DEFAULT_CSS_PROP_WHITELIST)

        return service

ckeditor_service_upgrader = CKEditorServiceUpgrader(VERSION,
                                                    'Silva CKEditor Service')
