# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workbench configuration seeds"""

from django.core.management.base import BaseCommand
from ghpcfe.models import MachineType, MachineTypeFlavour, MachineInstance
from django.utils.dateparse import parse_datetime
from django.db import transaction

import json
import subprocess
import re
import os
import hashlib
from collections import defaultdict

###################################################
# The purpose of this script is to populate the MachineType, MachineTypeInstace And MachineTypeFlavour models
# with information about the features supported by the various GCP VM types.
# https://cloud.google.com/compute/docs/reference/rest/v1/machineTypes
###################################################
#     todo: minimum disk sizes
# https://cloud.google.com/compute/docs/disks
###################################################
# Specifications for Tier 1 networking capable VMs
# SEE HERE: https://cloud.google.com/compute/docs/networking/configure-vm-with-high-bandwidth-configuration
#    todo: translate tables to bandwith speed data similar to SSD options below..?
tier1_vm_types = {'n2', 'n2d', 'c2', 'c2d', 'c3', 'c3d', 'm3', 'z3'}
tier1_minimum_cpus = 30
###################################################
# Fixed SSD machine types and disk counts
# SEE HERE: https://cloud.google.com/compute/docs/disks/local-ssd
fixed_ssd = {
    'c3-standard-4-lssd': [1],
    'c3-standard-8-lssd': [2],
    'c3-standard-22-lssd': [4],
    'c3-standard-44-lssd': [8],
    'c3-standard-88-lssd': [16],
    'c3-standard-176-lssd': [32],
    'c3d-standard-8-lssd': [1],
    'c3d-standard-16-lssd': [1],
    'c3d-standard-30-lssd': [2],
    'c3d-standard-60-lssd': [4],
    'c3d-standard-90-lssd': [8],
    'c3d-standard-180-lssd': [16],
    'c3d-standard-360-lssd': [32],
    'c3d-highmem-8-lssd': [1],
    'c3d-highmem-16-lssd': [1],
    'c3d-highmem-30-lssd': [2],
    'c3d-highmem-60-lssd': [4],
    'c3d-highmem-90-lssd': [8],
    'c3d-highmem-180-lssd': [16],
    'c3d-highmem-360-lssd': [32],
    'a3-highgpu-8g': [16],
    'a2-ultragpu-1g': [1],
    'a2-ultragpu-2g': [2],
    'a2-ultragpu-4g': [4],
    'a2-ultragpu-8g': [8],
    'z3-standard-88-lssd': [12],
    'z3-standard-176-lssd': [12]
}
###################################################
# Variable SSD machine types and valid disk count options
variable_ssd = {
    'n1-{type}-{vcpu}': [1, 2, 3, 4, 5, 6, 7, 8, 16, 24],
    'n2-{type}-2': [1, 2, 4, 8, 16, 24],
    'n2-{type}-4': [1, 2, 4, 8, 16, 24],
    'n2-{type}-8': [1, 2, 4, 8, 16, 24],
    'n2-{type}-16': [2, 4, 8, 16, 24],
    'n2-{type}-32': [4, 8, 16, 24],
    'n2-{type}-48': [8, 16, 24],
    'n2-{type}-64': [8, 16, 24],
    'n2-{type}-80': [8, 16, 24],
    'n2-{type}-96': [16, 24],
    'n2-{type}-128': [16, 24],
    'n2d-{type}-2': [1, 2, 4, 8, 16, 24],
    'n2d-{type}-4': [1, 2, 4, 8, 16, 24],
    'n2d-{type}-8': [1, 2, 4, 8, 16, 24],
    'n2d-{type}-16': [1, 2, 4, 8, 16, 24],
    'n2d-{type}-32': [2, 4, 8, 16, 24],
    'n2d-{type}-48': [2, 4, 8, 16, 24],
    'n2d-{type}-64': [4, 8, 16, 24],
    'n2d-{type}-80': [4, 8, 16, 24],
    'n2d-{type}-96': [8, 16, 24],
    'n2d-{type}-128': [8, 16, 24],
    'n2d-{type}-224': [8, 16, 24],
    'c2-{type}-4': [1, 2, 4, 8],
    'c2-{type}-8': [1, 2, 4, 8],
    'c2-{type}-16': [2, 4, 8],
    'c2-{type}-30': [4, 8],
    'c2-{type}-60': [8],
    'c2d-{type}-2': [1, 2, 4, 8],
    'c2d-{type}-4': [1, 2, 4, 8],
    'c2d-{type}-8': [1, 2, 4, 8],
    'c2d-{type}-16': [1, 2, 4, 8],
    'c2d-{type}-32': [2, 4, 8],
    'c2d-{type}-56': [4, 8],
    'c2d-{type}-112': [8],
    'a2-highgpu-1g': [1, 2, 4, 8],
    'a2-highgpu-2g': [2, 4, 8],
    'a2-highgpu-4g': [4, 8],
    'a2-highgpu-8g': [8],
    'a2-megagpu-16g': [8],
    'g2-standard-4': [1],
    'g2-standard-8': [1],
    'g2-standard-12': [1],
    'g2-standard-16': [1],
    'g2-standard-24': [2],
    'g2-standard-32': [1],
    'g2-standard-48': [4],
    'g2-standard-96': [8],
    'm1-megamem-96': [1, 2, 3, 4, 5, 6, 7, 8],
    'm3-ultramem-32': [4, 8],
    'm3-megamem-64': [4, 8],
    'm3-ultramem-64': [4, 8],
    'm3-megamem-128': [8],
    'm3-ultramem-128': [8]
}

###################################################

class Command(BaseCommand):
    help = "Runs gcloud compute machine-types to build a model of valid options for form submission when creating new clusters."

    def handle(self, *args, **options):
        self.stdout.write("Populating Machine Options...")
        data, no_change = self.get_data_from_gcloud()
        if no_change:
            self.stdout.write(self.style.ERROR('No changes to the machine-types hash were detected. Exiting gracefully.'))
            self.stdout.write(self.style.ERROR('If you have deployed OFE in this project you will need to delete existing metadata.'))
            self.stdout.write(self.style.ERROR('After deletion you can run the following command to populate the database model:'))
            self.stdout.write(self.style.ERROR('    /opt/gcluster/django-env/bin/python /opt/gcluster/hpc-toolkit/community/front-end/ofe/website/manage.py seed_machine_types'))
        elif data:
            variable_ssd_regex = self.compile_regex(variable_ssd)
            restructured_data = self.restructure_data(data, fixed_ssd, variable_ssd_regex)
            self.stdout.write(self.style.SUCCESS('Successfully restructured data'))
            self.save_data_to_models(restructured_data)
            self.stdout.write(self.style.SUCCESS('Successfully added VM info to models'))
        else:
            self.stdout.write(self.style.ERROR('No data retrieved from gcloud command.'))

    # Outputs the full VM names from the list above (ie. c2-standard-30 / c2-highmem-30 ...)
    def compile_regex(self, variable_ssd):
        pattern_mapping = {'{type}': '(standard|highmem|highcpu)', '{vcpu}': '\\d+'}
        regex_dict = {}
        for k, v in variable_ssd.items():
            pattern = k
            for key, regex in pattern_mapping.items():
                pattern = pattern.replace(key, regex)
            pattern += r'\b'
            regex_dict[re.compile(pattern)] = v
        return regex_dict

    # Finds matches based on VM types that support variable SSD counts and sets True
    def match_variable_ssd(self, vm_name, regex_dict):
        for pattern, disks in regex_dict.items():
            if pattern.match(vm_name):
                return True, disks
        return False, None

    # Determines whether VM is tier_1 networking compatible.
    # SEE HERE:  https://cloud.google.com/compute/docs/networking/configure-vm-with-high-bandwidth-configuration
    def is_tier1_compatible(self, item):
        vm_type_name = item['name']
        vm_type_prefix = vm_type_name.split('-')[0]
        return vm_type_prefix in tier1_vm_types and item['guestCpus'] >= tier1_minimum_cpus

    # Determines whether node placement is supported based on VM type
    def is_placement_supported(self, vm_name):
        placement_supported_vm_types = ["a2", "a3", "c2", "c3", "c2d", "c3d", "g2", "h3", "n2", "n2d"]
        return vm_name.split("-")[0] in placement_supported_vm_types

    # Runs the necessary gcloud command to pull the json info
    def get_data_from_gcloud(self):
        try:
            os.environ['GOOGLE_APP_CREDS'] = '/opt/gcluster/hpc-toolkit/community/front-end/ofe/credential.json'
            subprocess.run(
                ['gcloud', 'auth', 'activate-service-account', '--key-file=/opt/gcluster/hpc-toolkit/community/front-end/ofe/credential.json'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
            )
            result = subprocess.run(
                ['gcloud', 'compute', 'machine-types', 'list', '--quiet', '--filter=ZONE:-', '--format=json'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
            )

            # Check and update metadata
            no_change = not self.check_and_update_metadata(result.stdout)
            if no_change:
                return None, True
            
            return json.loads(result.stdout), False

        except subprocess.CalledProcessError as e:
            self.stderr.write(f"An error occurred while running gcloud command: {e.stderr}")
            return None, False

    # The following functions are used in conjunction with the cron job set during OFE deployment (in startup.sh).
    # This ensures that Django's models are only updated in the event that a change to machine-types is detected.
    #     IMPORTANT: For this to take place cleanly removal of metadata will need to also happen during OFE teardown.
    #                This should be possible to do using a shutdown script, although these are time-limited...
    #                See here: https://cloud.google.com/compute/docs/shutdownscript
    #                ALTERNATIVE: authenticate SA in startup.sh and scrub existing metadata during deployment?
    #                Also note, ensuring this script is updated in any deployed OFE instances would be crucial too.
    def get_project_metadata(self):
        """Fetch the current project metadata."""
        result = subprocess.run(
            ['gcloud', 'compute', 'project-info', 'describe', '--format=json'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        return json.loads(result.stdout)

    def get_hostname(self):
        """Fetch the hostname."""
        result = subprocess.run(
            ['hostname'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        return result.stdout.strip()

    def add_metadata(self, key, value):
        """Add metadata to the project."""
        subprocess.run(
            ['gcloud', 'compute', 'project-info', 'add-metadata', '--metadata', f'{key}={value}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )

    def get_existing_hash(self, metadata, key):
        """Extract the existing hash from the project metadata."""
        if 'commonInstanceMetadata' in metadata and 'items' in metadata['commonInstanceMetadata']:
            for item in metadata['commonInstanceMetadata']['items']:
                if item['key'] == key:
                    return item['value']
        return None

    def check_and_update_metadata(self, data):
        """Check and update project metadata if there are changes."""
        # Generate a hash from the result
        result_hash = hashlib.sha256(data.encode('utf-8')).hexdigest()

        # Fetch project metadata and hostname
        project_metadata = self.get_project_metadata()
        hostname = self.get_hostname()
        metadata_key = f'machine_types_{hostname}'

        # Get existing hash from metadata
        existing_hash = self.get_existing_hash(project_metadata, metadata_key)

        # Compare and update metadata if needed
        if existing_hash == result_hash:
            self.stdout.write("(Existing metadata in GCP project) No machine-type changes detected.")
            return False

        # Add new metadata
        self.add_metadata(metadata_key, result_hash)
        return True

    # Prepares machine data for insertion into Django's db
    def restructure_data(self, data, fixed_ssd, variable_ssd_regex):
        restructured_data = defaultdict(lambda: defaultdict(dict))
        for item in data:
            zone = item['zone']
            vm_name = item['name']

            zone_parts = zone.split('-')
            cloud_region = '-'.join(zone_parts[:2])
            cloud_zone = zone_parts[-1]

            item['cloud_region'] = cloud_region
            item['cloud_zone'] = cloud_zone
            item['memoryGb'] = int(item.get('memoryMb', 0) / 1024)
            item['tier_1_compatible'] = self.is_tier1_compatible(item)
            item['gcp_id'] = item.pop('id', None)

            accelerators = item.get('accelerators', [])
            if accelerators:
                accelerator = accelerators[0]
                item['guestAcceleratorCount'] = accelerator.get('guestAcceleratorCount', 0)
                item['guestAcceleratorType'] = accelerator.get('guestAcceleratorType', '')

            local_ssd = 'none'
            num_disks = '[0]'
            if vm_name in fixed_ssd:
                local_ssd = 'fixed'
                num_disks = fixed_ssd[vm_name]
            else:
                match, disks = self.match_variable_ssd(vm_name, variable_ssd_regex)
                if match:
                    local_ssd = 'variable'
                    num_disks = disks

            item['local_ssd'] = local_ssd
            item['number_of_local_ssd_disks'] = num_disks

            restructured_data[zone][vm_name] = item

        self.stdout.write(self.style.SUCCESS(f'Restructured data for {len(restructured_data)} zones'))
        return restructured_data

    @transaction.atomic
    def save_data_to_models(self, restructured_data):
        flavour_cache = {}
        machine_type_cache = {}
        for zone, vm_data in restructured_data.items():
            for vm_name, item in vm_data.items():
                flavour_key = (
                    vm_name,
                    item.get('guestCpus', 0),
                    item.get('memoryMb', 0),
                    item.get('guestAcceleratorCount', 0),
                    item.get('guestAcceleratorType', ''),
                    item.get('local_ssd', 'none')
                )
                
                if flavour_key not in flavour_cache:
                    flavour, created = MachineTypeFlavour.objects.get_or_create(
                        vm_name=flavour_key[0],
                        guestCpus=flavour_key[1],
                        memoryMb=flavour_key[2],
                        guestAcceleratorCount=flavour_key[3],
                        guestAcceleratorType=flavour_key[4],
                        local_ssd=flavour_key[5],
                        defaults={
                            'description': item.get('description', ''),
                            'gcp_id': item.get('gcp_id', ''),
                            'memoryGb': item.get('memoryGb', 0),
                            'maximumPersistentDisks': item.get('maximumPersistentDisks', 0),
                            'maximumPersistentDisksSizeGb': item.get('maximumPersistentDisksSizeGb', ''),
                            'imageSpaceGb': item.get('imageSpaceGb', 0),
                            'isSharedCpu': item.get('isSharedCpu', False),
                            'tier_1_compatible': item.get('tier_1_compatible', False),
                            'number_of_local_ssd_disks': item.get('number_of_local_ssd_disks', 0),
                            'placement_support': self.is_placement_supported(vm_name),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created flavour: {flavour} with gcp_id: {flavour.gcp_id}'))
                    flavour_cache[flavour_key] = flavour
                else:
                    flavour = flavour_cache[flavour_key]

                if vm_name not in machine_type_cache:
                    machine_type, created = MachineType.objects.get_or_create(
                        name=vm_name,
                        flavour=flavour,
                        defaults={
                            'kind': item.get('kind', ''),
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created machine type: {machine_type.name} with flavour: {flavour}'))
                    machine_type_cache[vm_name] = machine_type
                else:
                    machine_type = machine_type_cache[vm_name]

                MachineInstance.objects.get_or_create(
                    machine_type=machine_type,
                    zone=zone,
                    cloud_region=item['cloud_region'],
                    cloud_zone=item['cloud_zone'],
                    selfLink=item['selfLink']  # Store selfLink here
                )

        self.stdout.write(self.style.SUCCESS('Data successfully saved to models'))
