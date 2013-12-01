import hashlib

from django.conf import settings

# Customisable settings - see reference.markdown

USE_SITES_FRAMEWORK = getattr(settings, 'ADHOC_USE_SITES_FRAMEWORK', False)
TINYMCE_BUTTONS = getattr(settings, 'ADHOC_TINYMCE_BUTTONS', "formatselect,bold,italic,|,undo,redo,|,link,|,blockquote,bullist,numlist,|,pastetext,code")
TINYMCE_CONTENT_CSS = getattr(settings, 'ADHOC_TINYMCE_CONTENT_CSS', "")
POST_EDIT_CALLBACK = getattr(settings, 'ADHOC_POST_EDIT_CALLBACK', '""')
MAX_IMAGE_DIMENSIONS = getattr(settings, 'ADHOC_MAX_IMAGE_DIMENSIONS', (1920, 1200))
BLOCK_REQUIRED_CALLBACK = getattr(settings, 'ADHOC_BLOCK_REQUIRED_CALLBACK', None)
IMAGE_REQUIRED_CALLBACK = getattr(settings, 'ADHOC_IMAGE_REQUIRED_CALLBACK', None)
DUMMY_IMAGE_SOURCE = getattr(settings, 'ADHOC_DUMMY_IMAGE_SOURCE', None)


# The following are for internal use and shouldn't need to be customised

STATIC_URL = getattr(settings, 'ADHOC_STATIC_URL', settings.STATIC_URL + 'cms/')
SECRET_KEY = getattr(settings, 'SECRET_KEY', 'just in case?')
UPLOAD_PATH = getattr(settings, 'ADHOC_UPLOAD_PATH', 'uploads/%Y_%m')
HIGHLIGHT_COLOR = getattr(settings, 'ADHOC_HIGHLIGHT_COLOR', "#ff0")
SITE_ID = getattr(settings, 'SITE_ID', 1)

# let's be *really* careful not to display content from another site using the same cache
CACHE_PREFIX = 'cms-%s' % hashlib.sha1(settings.SECRET_KEY).hexdigest()[:5]

