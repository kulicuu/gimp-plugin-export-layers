# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2015 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

str = unicode

import inspect
import os
import shutil
import unittest

import gimp

pdb = gimp.pdb

from ..pygimplib import pgfileformats
from ..pygimplib import pgitemdata
from ..pygimplib import pgpdb
from ..pygimplib import pgsettinggroup

from .. import exportlayers
from .. import settings_plugin

#===============================================================================

_current_module_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(_current_module_dir)), "resources")
TEST_IMAGES_DIR = os.path.join(RESOURCES_DIR, "Test images")

EXPECTED_RESULTS_DIR = os.path.join(TEST_IMAGES_DIR, "Expected results")
OUTPUT_DIR = os.path.join(TEST_IMAGES_DIR, "Temp output")

#===============================================================================


class TestExportLayersCompareLayerContents(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    pdb.gimp_context_push()
    
    cls.test_image_filename = os.path.join(TEST_IMAGES_DIR, "test_export_layers_contents.xcf")
    cls.test_image = cls._load_image()
    
    cls.output_directory = OUTPUT_DIR
    
    if os.path.exists(cls.output_directory) and os.listdir(cls.output_directory):
      raise ValueError("Directory for temporary results '{0}' must be empty".format(cls.output_directory))
    
    cls.default_expected_layers_dir = EXPECTED_RESULTS_DIR
    # key: directory containing expected results
    # value: gimp.Image instance
    cls.expected_images = {}
  
  @classmethod
  def tearDownClass(cls):
    pdb.gimp_image_delete(cls.test_image)
    for image in cls.expected_images.values():
      pdb.gimp_image_delete(image)
    
    pdb.gimp_context_pop()
  
  def setUp(self):
    self.image_with_results = None
  
  def tearDown(self):
    if self.image_with_results is not None:
      pdb.gimp_image_delete(self.image_with_results)
    if os.path.exists(self.output_directory):
      shutil.rmtree(self.output_directory)
  
  def test_default_settings(self):
    self.compare()
  
  def test_ignore_layer_modes(self):
    self.compare({
                   'ignore_layer_modes': True
                 },
                 [('overlay', 'overlay_ignore-layer-modes')])
  
  def test_autocrop(self):
    self.compare({
                   'autocrop': True
                 },
                 [('left-frame-with-extra-borders', 'left-frame-with-extra-borders_autocrop'),
                  ('main-background', 'main-background_autocrop')])
  
  def test_use_image_size(self):
    self.compare({
                   'use_image_size': True
                 },
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'use_image_size'))
  
  def test_use_image_size_autocrop(self):
    self.compare({
                   'use_image_size': True,
                   'autocrop': True
                 },
                 [('left-frame-with-extra-borders', 'left-frame-with-extra-borders_autocrop'),
                  ('main-background', 'main-background_autocrop')],
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'use_image_size'))
  
  def test_merge_layer_groups(self):
    self.compare({
                   'merge_layer_groups': True
                 },
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'merge_layer_groups'))
  
  def test_background(self):
    self.compare({
                   'tagged_layers_mode': 1
                 },
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'background'))
  
  def test_background_autocrop(self):
    self.compare({
                   'tagged_layers_mode': 1,
                   'autocrop': True
                 },
                 [('bottom-frame-semi-transparent', 'bottom-frame-semi-transparent_background_autocrop'),
                  ('left-frame-with-extra-borders', 'left-frame-with-extra-borders_autocrop')])
  
  def test_background_autocrop_use_image_size(self):
    self.compare({
                   'tagged_layers_mode': 1,
                   'autocrop': True,
                   'use_image_size': True
                 },
                 [('left-frame-with-extra-borders', 'left-frame-with-extra-borders_autocrop_use-image-size')],
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'background'))
  
  def test_background_autocrop_crop_to_background(self):
    self.compare({
                   'tagged_layers_mode': 1,
                   'autocrop': True,
                   'crop_mode': 1
                 },
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'background',
                                                   'crop_mode'))
  
  def test_background_autocrop_crop_to_background_use_image_size(self):
    self.compare({
                   'tagged_layers_mode': 1,
                   'autocrop': True,
                   'crop_mode': 1,
                   'use_image_size': True
                 },
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'background',
                                                   'crop_mode', 'use_image_size'))
  
  def test_foreground(self):
    layer_data = pgitemdata.LayerData(self.test_image)
    for layer_elem in layer_data:
      layer_elem.item.name = layer_elem.item.name.replace("[background]", "[foreground]")
    
    self.compare({
                   'tagged_layers_mode': 1
                 },
                 expected_results_dir=os.path.join(self.default_expected_layers_dir, 'foreground'))
    
    self._reload_image()
  
  def compare(self, different_settings=None, different_results_and_expected_layers=None,
              expected_results_dir=None):
    settings = settings_plugin.create_settings()
    settings['special']['image'].set_value(self.test_image)
    settings['main']['output_directory'].set_value(self.output_directory)
    
    if different_settings is not None:
      for setting_name, setting_value in different_settings.items():
        settings['main'][setting_name].set_value(setting_value)
    
    if expected_results_dir is None:
      expected_results_dir = self.default_expected_layers_dir
    
    if expected_results_dir not in self.expected_images:
      self.expected_images[expected_results_dir], expected_layers = (
        self._load_layers_from_dir(expected_results_dir))
    else:
      expected_layers = {layer.name: layer for layer in self.expected_images[expected_results_dir].layers}
    
    param_values = pgsettinggroup.PdbParamCreator.list_param_values([settings])
    pdb.plug_in_export_layers(*param_values)
    
    self.image_with_results, layers = self._load_layers_from_dir(self.output_directory)
    
    if different_results_and_expected_layers is not None:
      for layer_name, expected_layer_name in different_results_and_expected_layers:
        expected_layers[layer_name] = expected_layers[expected_layer_name]
    
    for layer in layers.values():
      self._compare_layers(layer, expected_layers[layer.name])
  
  def _compare_layers(self, layer, expected_layer):
    self.assertEqual(pgpdb.compare_layers([layer, expected_layer]), True,
      msg=("Layers are not identical:\n"
           "processed layer: {0}\n"
           "expected layer: {1}"
           .format(layer.name, expected_layer.name)))
  
  @classmethod
  def _load_image(cls):
    return pdb.gimp_file_load(cls.test_image_filename, os.path.basename(cls.test_image_filename))
  
  @classmethod
  def _reload_image(cls):
    cls.test_image = cls._load_image()
  
  @classmethod
  def _load_layers(cls, layers_filenames):
    """
    Load layers from specified filenames into a new image. Return the image and
    a dict with (layer name: gimp.Layer instance) pairs.
    """
    
    image = pgpdb.load_layers(layers_filenames, image=None, strip_file_extension=True)
    return image, {layer.name: layer for layer in image.layers}
  
  @classmethod
  def _load_layers_from_dir(cls, layers_dir):
    return cls._load_layers(cls._list_layers_files(layers_dir))
  
  @classmethod
  def _list_layers_files(cls, layers_dir):
    layers_files = []
    
    for filename in os.listdir(layers_dir):
      path = os.path.join(layers_dir, filename)
      if os.path.isfile(path):
        layers_files.append(path)
    
    return layers_files


#===============================================================================


def test_file_formats(layer_exporter, export_settings):
  orig_output_directory = export_settings['output_directory'].value
  
  for file_format in pgfileformats.file_formats:
    for file_extension in file_format.file_extensions:
      export_settings['file_extension'].set_value(file_extension)
      export_settings['output_directory'].set_value(os.path.join(orig_output_directory, file_extension))
      try:
        layer_exporter.export_layers()
      except exportlayers.ExportLayersError:
        # Do not stop execution when one file format causes an error.
        continue
