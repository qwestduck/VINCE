from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import resolve

class StructureMatchedViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def post(self, **fill):
        return resolve(self.url).func(
            self.factory.post(
                self.url, self.fill_pattern(**fill), content_type=self.content_type
            )
        )

    def fill_pattern(self, *args, **kwargs):
        raise NotImplementedError
