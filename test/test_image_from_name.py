import unittest

import provision.nodelib as nodelib

class MockImage(object):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name

class Test(unittest.TestCase):

    def setUp(self):

        self.name = 'default-image'

        self.numbered_images = map(MockImage, [
                'default-image0',
                'default-image1',
                'default-image10',
                'default-image9'])

        self.mixed_images = map(MockImage, [
                'default-image',
                'default-image1',
                'default-image10',
                'default-image9'])

        self.inconsistently_numbered_images = map(MockImage, [
                'default-image_0',
                'default-image-11',
                'default-image_12',
                'default-image13'])

    def test_image_from_name_numbered(self):
        assert 'default-image10' == nodelib.image_from_name(
            self.name, self.numbered_images).name

    def test_image_from_name_mixed(self):
        assert 'default-image' == nodelib.image_from_name(
            self.name, self.mixed_images).name

    def test_image_from_name_inconsistent(self):
        assert 'default-image13' == nodelib.image_from_name(
            self.name, self.inconsistently_numbered_images).name
