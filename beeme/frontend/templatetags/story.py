# django imports
from django import template
from django.utils.safestring import mark_safe
# third-party imports
from constance import config


register = template.Library()


@register.simple_tag
def story_intro():
	html1 = config.STORY_INTRO

	return mark_safe(html1)
