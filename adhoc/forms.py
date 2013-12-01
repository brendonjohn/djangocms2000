import re

from django import forms
from django.conf import settings
from django.core.urlresolvers import resolve, Resolver404
from django.utils.safestring import mark_safe

from models import Page, Block, Image, template_choices
import settings as cms_settings

class ReadonlyInput(forms.widgets.HiddenInput):
    is_hidden = False
    def __init__(self, attrs=None, model=None, display_text=None):
        super(ReadonlyInput, self).__init__(attrs)
        self.model = model
        self.display_text = display_text
        
    def render(self, name, value, attrs=None):
        if self.display_text:
            text_value = self.display_text          
        elif self.model:
            text_value = self.model.objects.get(pk=value)
        else:
            text_value = value
        return mark_safe("<p>%s</p>%s" % (text_value, super(ReadonlyInput, self).render(name, value, attrs)))


class BlockForm(forms.ModelForm):
	class Meta:
	    model = Block
	    fields = ('content', )


class ImageForm(forms.ModelForm):
	class Meta:
	    model = Image
	    fields = ('file', 'description', )


URL_STRIP_REGEX = re.compile('[^A-z0-9\-_\/\.]')
URL_DASH_REGEX = re.compile('--+')
class PageForm(forms.ModelForm):
    template = forms.CharField(
        widget=forms.Select(choices=template_choices()),
        required=False
    )
    def __init__(self, *args, **kwargs):
        super(PageForm, self).__init__(*args, **kwargs)
        
        # just in case a template has been added/changed since last server restart
        self.fields['template'].widget.choices = template_choices()
                
        # if the page is rendered by an actual django url, make template and url read-only
        instance = kwargs.get('instance', None)
        if instance:
            try:
                resolve(instance.url)
            except Resolver404, e:
                # must be an admin-created page, rendered by the middleware
                pass
            else:
                # must be a django-created page, rendered by a urlconf
                self.fields['url'].widget = ReadonlyInput()
                self.fields['url'].help_text = ''

                # TODO hide/delete these rather than showing them as readonly?
                self.fields['template'].widget = ReadonlyInput(display_text='n/a')
                self.fields['template'].help_text = ''
                self.fields['is_live'].widget = ReadonlyInput(display_text='n/a')
                self.fields['is_live'].help_text = ''
        
    class Meta:
        model = Page
    
    def clean(self):
        data = self.cleaned_data
        if not data.get('template', None) and data.get('url', None):
            # TODO: this may fail if creating a page for a different site with
            # different urls
            try:
                resolve(data['url'])
            except Resolver404, e:
                err = 'This field is required for admin-created pages.'
                self._errors['template'] = self.error_class([err])
        
        # validate url/site uniqueness
        url = URL_STRIP_REGEX.sub('', data['url'].replace(' ', '-')).lower()
        url = URL_DASH_REGEX.sub('-', url).strip('-')
        
        url = ("/%s" % (url.lstrip('/'))).replace('//', '/')
        
        # WARNING: this assumes the APPEND_SLASH setting is common across sites
        if settings.APPEND_SLASH and not url.endswith('/'):
            url = "%s/" % url
        
        if cms_settings.USE_SITES_FRAMEWORK:
            site_pages = Page.objects.filter(sites__in=data['sites'])
        else:
            site_pages = Page.objects.all()
        
        if self.instance:
            site_pages = site_pages.exclude(pk=self.instance.pk)
                
        # for the purposes of uniqueness, test both slashed and non-slashed urls
        test_urls = [url.rstrip('/'), "%s/" % url.rstrip('/')]
        clashes = site_pages.filter(url__in=test_urls)
        if clashes:
            sites = clashes.values_list('sites__domain', flat=True)
            err = 'A page with this url already exists for %s.' % ', '.join(sites)
            self._errors['url'] = self.error_class([err])
        
        data['url'] = url
        
        #raise Exception
        
        return data
        


class PublicPageForm(PageForm):
    class Meta(PageForm.Meta):
        exclude = ['site',]
    
    
    
