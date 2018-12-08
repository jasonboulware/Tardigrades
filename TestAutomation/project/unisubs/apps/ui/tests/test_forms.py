from django.test import TestCase

from nose.tools import *
import mock

from ui.forms import ManagementForm
from utils.factories import *
from videos.models import Video

class TestVideoManagementForm(TestCase):
    def setUp(self):
        # make a bunch of videos to use as objects for the form to act on
        self.videos = [VideoFactory() for i in range(5)]
        self.qs = Video.objects.filter(id__in=[v.id for v in self.videos])

    def build_form(self, selected_videos, all_selected=False, data=None):
        selection = [v.id for v in selected_videos]
        form = ManagementForm(self.qs, selection, all_selected, data=data)
        if data is not None:
            if not form.is_valid():
                raise ValidationError()
        return form

    def test_iter_objects(self):
        form = self.build_form(self.videos[0:4], data={})
        assert_items_equal(form.iter_objects(), self.videos[0:4])

    def test_iter_objects_include_all(self):
        form = self.build_form(self.videos[0:4], all_selected=True,
                               data={'include_all': True})
        assert_items_equal(form.iter_objects(), self.videos)

    def test_enable_include_all_logic(self):
        # enabled it if all objects on the page are selected
        form = self.build_form(self.videos[0:4], all_selected=True)
        assert_true('include_all' in form.fields)
        # but not if there are no objects on other pages
        form = self.build_form(self.videos, all_selected=True)
        assert_false('include_all' in form.fields)
        # disabled it if all objects are not selected
        form = self.build_form(self.videos[0:4], all_selected=False)
        assert_false('include_all' in form.fields)

    def tets_submit(self):
        form = self.build_form(self.videos[0:4], data={})
        def perform_submit(objects):
            assert_equal(list(objects), self.videos[0:4])
        form.perform_submit = perform_submit
        form.submit()

    def test_submit_with_progress_callback(self):
        form = self.build_form(self.videos[0:4], data={})
        progress_callback = mock.Mock()
        def perform_submit(objects):
            for i, obj in enumerate(objects):
                assert_equal(obj, self.videos[i])
                assert_equal(progress_callback.call_args, mock.call(i, 4))
        form.perform_submit = perform_submit
        form.submit(progress_callback)
        assert_equal(progress_callback.call_args, mock.call(4, 4))
