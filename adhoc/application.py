# -*- coding: utf-8 -*-

import os
import functools

from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils.safestring import mark_safe

from models import Block, Image, Page
from utils import is_editing, generate_cache_key
import settings as cms_settings


def get_block_or_image(model_cls, label, url=None, site_id=None, related_object=None, cached=True):
    '''Get a page, site or generic block/image, based on any one of the optional arguments.'''
    
    key = generate_cache_key(model_cls._meta.module_name, label, url=url, site_id=site_id, related_object=related_object)
    
    obj = cache.get(key)
    if obj == None or not cached:
        if url:
            ctype = ContentType.objects.get_for_model(Page)
            object_id = Page.objects.get_for_url(url).pk
        elif site_id:
            ctype = ContentType.objects.get(app_label='sites', model='site')
            object_id = site_id
        elif related_object:
            ctype = ContentType.objects.get_for_model(related_object)
            object_id = related_object.id
        else:
            raise TypeError(u'One of url, site_id or related_object is required')
        
        obj = model_cls.objects.get_or_create(label=label, content_type=ctype,
                                           object_id=object_id)[0]
        
        cache.set(key, obj)
    return obj

get_block = functools.partial(get_block_or_image, Block)
get_image = functools.partial(get_block_or_image, Image)


def get_lookup_kwargs(site_id=None, related_object=None, request=None):
    '''Converts arguments passed through from a template into a dict of 
       arguments suitable for passing to the get_block_or_image function.'''
       
    if related_object:
        return {'related_object': related_object}
    elif site_id:
        return {'site_id': site_id}
    elif request:
        return {'url': request.path_info}
    else:
        raise TypeError(u"You must provide one of request, site_id or related_object.")
        

def default_block_renderer(block, filters=None):
    content = block.display_content()
    if filters and content:
        for f in filters.split('|'):
            content = getattr(template.defaultfilters, f)(content)
    return content


def set_block_format(block, format):
    '''Sets block format, naively assuming that the same block is not defined
       elsewhere with a different format (which would be idiotic anyway.)'''
    
    if block.format != format:
        block.format = format
        block.save()


def get_rendered_block(label, format='plain', related_object=None, filters=None,
                       editable=None, renderer=None, site_id=None,
                       request=None):
    '''Get the rendered html for a block, wrapped in editing bits if appropriate.
       `renderer` is a callable taking a block object and returning rendered html
       for the block.'''
    
    if format not in [t[0] for t in Block.FORMAT_CHOICES]:
       raise LookupError('%s is not a valid block format.' % format)
    
    if editable == None:
        editable = (format != 'attr')
    
    editing = editable and request and is_editing(request, 'block')
    lookup_kwargs = get_lookup_kwargs(site_id, related_object, request)
    
    if not renderer:
        renderer = functools.partial(default_block_renderer, filters=filters)
    
    if editing:
        block = get_block(label, cached=False, **lookup_kwargs)
        set_block_format(block, format)
        return template.loader.render_to_string("cms/cms/block_editor.html", {
            'block': block,
            'rendered_content': renderer(block),
        })
    else:
        block = get_block(label, **lookup_kwargs)
        set_block_format(block, format)
        return renderer(block)


class RenderedImage:
    '''A wrapper class for Image which can optionally be resized, via the geometry and 
       crop arguments. If these are given, the url, height and width are derived from a 
       generated sorl thumbnail; otherwise the original image is used. The height and
       width are also divided by the scale argument, if provided, to enable retina
       images.'''
    
    def __init__(self, image, geometry=None, crop=None, scale=1):
        if type(geometry) == int:
            geometry = str(geometry)
        
        self.image = image
        self.geometry = geometry
        self.crop = crop
        self.scale = scale
        
    def get_thumbnail(self):
        if self.geometry:
            from sorl.thumbnail import get_thumbnail
            return get_thumbnail(self.image.file, self.geometry, crop=self.crop)
        else:
            return None
    
    def get_image_attr(self, attr):
        if self.image.file:
            thumb = self.get_thumbnail()
            return getattr(thumb, attr) if thumb else getattr(self.image.file, attr)
        else:
            return None
    
    @property
    def url(self):
        return self.get_image_attr('url')
    
    @property
    def width(self):
        return self.get_image_attr('width') / self.scale
    
    @property
    def height(self):
        return self.get_image_attr('height') / self.scale

    def as_tag(self):
        return default_image_renderer(self)


def get_dummy_image(geometry):
    # geometry can be of the form 'XxY', 'X' or 'xY'. if only one dimension is supplied, 
    # return a square
    width, height = (geometry.split('x') + [''])[:2]
    placeholder = cms_settings.DUMMY_IMAGE_SOURCE % {
        'width': width or height,
        'height': height or width,
    }
    return mark_safe('<img class="placeholder" '\
                'src="%s" alt="%s" width="%s" height="%s">' % (placeholder, 
                                                               'Placeholder image',
                                                               width or height,
                                                               height or width))

def default_image_renderer(img):
    if cms_settings.DUMMY_IMAGE_SOURCE and img.geometry and \
       (not img.image.file or not os.path.exists(img.image.file.path)):
        return get_dummy_image(img.geometry)
    elif img.url:
        return mark_safe('<img src="%s" alt="%s" width="%s" height="%s">' % (img.url, 
                                                                   img.image.description,
                                                                   img.width,
                                                                   img.height))
    else:
        return ''

def get_rendered_image(label, geometry=None, related_object=None, crop=None,
                       editable=True, renderer=default_image_renderer,
                       site_id=None, request=None, scale=1):
    '''Get the rendered html for an image, wrapped in editing bits if appropriate.
       `renderer` is a callable taking an image object, geometry and crop options,
       and returning rendered html for the image.'''

    editing = editable and request and is_editing(request, 'image')
    lookup_kwargs = get_lookup_kwargs(site_id, related_object, request)

    if editing:
        image = get_image(label, cached=False, **lookup_kwargs)
        rendered_content = renderer(RenderedImage(image, geometry, crop, scale))
    
        return template.loader.render_to_string("cms/cms/image_editor.html", {
            'image': image,
            'rendered_content': rendered_content,
        })
    else:
        return renderer(RenderedImage(get_image(label, **lookup_kwargs), geometry, crop, scale))
