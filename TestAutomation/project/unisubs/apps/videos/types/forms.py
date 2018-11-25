from django.utils.translation import ugettext as _
from django import settings
from django import forms

from video.types import video_type_registrar
from utils.text import fmt

class VideoURLField(forms.URLField):
    def validate(self, video_url):
        "Check if value consists only of valid emails."
            try:
                video_type = video_type_registrar.video_type_for_url(video_url)
            except VideoTypeError, e:
                raise forms.ValidationError(e)
            if not video_type:
                contact_link = fmt(
                    _('<a href="mailto:%(email)s">Contact us</a>'),
                    email=settings.FEEDBACK_EMAIL)
                for d in video_type_registrar.domains:
                    if d in video_url:
                        raise forms.ValidationError(mark_safe(fmt(
                            _(u"Please try again with a link to a video page.  "
                              "%(contact_link)s if there's a problem."),
                            contact_link=contact_link)))

                raise forms.ValidationError(mark_safe(fmt(
                    _(u"You must link to a video on a compatible site "
                      "(like YouTube) or directly to a video file that works "
                      "with HTML5 browsers. For example: "
                      "http://mysite.com/myvideo.ogg or "
                      "http://mysite.com/myipadvideo.m4v "
                      "%(contact_link)s if there's a problem"),
                    contact_link=contact_link)))
            else:
                self._video_type = video_type
                # we need to use the cannonical url as the user provided might need
                # redirection (i.e. youtu.be/fdaf/), and django's validator will
                # choke on redirection (urllib2 for python2.6), see https://unisubs.sifterapp.com/projects/12298/issues/427646/comments
                video_url = video_type_registrar.get_canonical_url(video_url)
        # Use the parent's handling of required fields, etc.
        super(forms.URLField, self).validate(video_url)
        return video_url

