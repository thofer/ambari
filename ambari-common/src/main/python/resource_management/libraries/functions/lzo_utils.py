#!/usr/bin/env python
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Ambari Agent

"""
__all__ = ["should_install_lzo", "get_lzo_packages", "install_lzo_if_needed"]

from ambari_commons.os_check import OSCheck
from resource_management.libraries.functions.stack_features import check_stack_feature
from resource_management.libraries.functions.default import default
from resource_management.libraries.functions import StackFeature, stack_features
from resource_management.libraries.script.script import Script
from resource_management.core.logger import Logger
from resource_management.libraries.functions.expect import expect
from resource_management.core.resources.packaging import Package

INSTALLING_LZO_WITHOUT_GPL = "Cannot install LZO.  The GPL license must be explicitly enabled using 'ambari-server setup' on the Ambari host, then restart the server and try again."

def get_lzo_packages():
  lzo_packages = []
  script_instance = Script.get_instance()
  if OSCheck.is_suse_family() and int(OSCheck.get_os_major_version()) >= 12:
    lzo_packages += ["liblzo2-2", "hadoop-lzo-native"]
  elif OSCheck.is_redhat_family() or OSCheck.is_suse_family():
    lzo_packages += ["lzo", "hadoop-lzo-native"]
  elif OSCheck.is_ubuntu_family():
    lzo_packages += ["liblzo2-2"]


  stack_version_unformatted = stack_features.get_stack_feature_version(Script.get_config()) # only used to check stack_feature, NOT as package version!
  if stack_version_unformatted and check_stack_feature(StackFeature.ROLLING_UPGRADE, stack_version_unformatted):
    if OSCheck.is_ubuntu_family():
      lzo_packages += [script_instance.format_package_name("hadooplzo-${stack_version}") ,
                       script_instance.format_package_name("hadooplzo-${stack_version}-native")]
    else:
      lzo_packages += [script_instance.format_package_name("hadooplzo_${stack_version}"),
                       script_instance.format_package_name("hadooplzo_${stack_version}-native")]
  else:
    lzo_packages += ["hadoop-lzo"]

  return lzo_packages

def should_install_lzo():
  """
  Return true if lzo is enabled via core-site.xml and GPL license (required for lzo) is accepted.
  """
  config = Script.get_config()
  io_compression_codecs = default("/configurations/core-site/io.compression.codecs", None)
  lzo_enabled = io_compression_codecs is not None and "com.hadoop.compression.lzo" in io_compression_codecs.lower()

  if not lzo_enabled:
    return False

  is_gpl_license_accepted = default("/hostLevelParams/gpl_license_accepted", False)
  if not is_gpl_license_accepted:
    Logger.warning(INSTALLING_LZO_WITHOUT_GPL)
    return False

  return True

def install_lzo_if_needed():
  """
  Install lzo package if {#should_install_lzo} is true
  """
  if not should_install_lzo():
    return

  lzo_packages = get_lzo_packages()

  config = Script.get_config()
  agent_stack_retry_on_unavailability = config['hostLevelParams']['agent_stack_retry_on_unavailability']
  agent_stack_retry_count = expect("/hostLevelParams/agent_stack_retry_count", int)

  Package(lzo_packages,
          retry_on_repo_unavailability=agent_stack_retry_on_unavailability,
          retry_count=agent_stack_retry_count
  )
