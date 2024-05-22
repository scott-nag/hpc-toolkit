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
""" admin.py """

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *  #pylint: disable=wildcard-import,unused-wildcard-import
from .forms import UserCreationForm, UserUpdateForm


class UserAdmin(BaseUserAdmin):
    """ Custom UserAdmin """
    add_form = UserCreationForm
    form = UserUpdateForm
    model = User
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "email",
        "is_staff",
        "is_active",
    )
    ordering = ("username",)
    readonly_fields = (
        "last_login",
        "date_joined",
    )

    fieldsets = (
        (None, {
            "fields": (
                "username",
                "password",
            )
        }),
        ("Personal info", {
            "fields": (
                "first_name",
                "last_name",
                "email",
            )
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "roles",
            )
        }),
        ("Important dates", {
            "fields": ("last_login", "date_joined")
        }),
    )


class MountPointInline(admin.TabularInline):
    """ To enable inline editing of instance types on cluster admin page """
    model = MountPoint
    extra = 1


class ClusterPartitionInline(admin.TabularInline):
    """ To enable inline editing of instance types on cluster admin page """
    model = ClusterPartition
    extra = 1


class FilesystemExportInline(admin.TabularInline):
    """ To enable inline editing of instance types on cluster admin page """
    model = FilesystemExport
    extra = 1


class VirtualNetworkAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for VirtualNetwork model """
    list_display = ("id", "name", "cloud_region", "cloud_id", "cloud_state")


class VirtualSubnetAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for VirtualSubnet model """
    list_display = ("id", "name", "cloud_zone", "cloud_id", "_vpc_name",
                    "cloud_state")

    def _vpc_name(self, obj):
        return obj.vpc.name

    _vpc_name.short_description = "VPC"


class FilesystemAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for Filesystem model """
    inlines = (FilesystemExportInline,)

    list_display = ("id", "name", "impl_type", "cloud_zone", "cloud_id",
                    "subnet", "cloud_state")


class ClusterAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for Cluster model """
    inlines = (MountPointInline, ClusterPartitionInline)
    list_display = ("id", "name", "cloud_zone", "_controller_node", "status")

    def _controller_node(self, obj):
        if obj.controller_node:
            return (obj.controller_node.public_ip
                    if obj.controller_node.public_ip else
                    obj.controller_node.internal_ip)
        else:
            return "<none>"

    _controller_node.short_description = "Controller Node IP"


class ApplicationAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for Application model """
    list_display = ("id", "name", "install_loc", "compiler", "mpi", "status")


class SpackApplicationAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for Application model """
    list_display = ("id", "name", "spack_spec", "install_loc", "compiler",
                    "mpi", "status")


class JobAdmin(admin.ModelAdmin):
    """ Custom ModelAdmin for Job model """
    list_display = ("id", "get_name", "partition", "number_of_nodes",
                    "ranks_per_node", "threads_per_rank", "status")

    def get_name(self, obj):
        return obj.application.name

    get_name.short_description = "Application"  #Renames column head

class MachineTypeAdmin(admin.ModelAdmin):
    """ Custom Admin for MachineType model """
    list_display = ('name', 'kind', 'flavour')
    list_filter = ('name', 'kind', 'flavour')
    search_fields = ('name', 'kind', 'flavour__description')

class MachineTypeFlavourAdmin(admin.ModelAdmin):
    """ Custom Admin for MachineTypeFlavour model """
    list_display = (
        'vm_name', 'guestCpus', 'memoryGb', 'guestAcceleratorCount', 'guestAcceleratorType',
        'local_ssd', 'number_of_local_ssd_disks', 'maximumPersistentDisks', 'maximumPersistentDisksSizeGb',
        'tier_1_compatible', 'description', 'isSharedCpu', 'imageSpaceGb', 'get_machine_types',
        'placement_support'
    )
    list_filter = (
        'vm_name', 'guestCpus', 'memoryGb', 'guestAcceleratorType', 'tier_1_compatible'
    )
    search_fields = ('vm_name', 'gcp_id', 'description')

    def get_machine_types(self, obj):
        return ", ".join(set([mt.name for mt in obj.machine_types.all()]))
    get_machine_types.short_description = 'Machine Types'

class MachineInstanceAdmin(admin.ModelAdmin):
    """ Custom Admin for MachineInstance model """
    list_display = ('machine_type', 'zone', 'cloud_region', 'cloud_zone', 'selfLink')
    list_filter = ('machine_type', 'zone', 'cloud_region', 'cloud_zone')
    search_fields = ('machine_type__name', 'zone', 'cloud_region', 'cloud_zone', 'selfLink')


# Register your models here.
admin.site.register(Application, ApplicationAdmin)
admin.site.register(SpackApplication, SpackApplicationAdmin)
admin.site.register(CustomInstallationApplication)
admin.site.register(ApplicationInstallationLocation)
admin.site.register(VirtualNetwork, VirtualNetworkAdmin)
admin.site.register(VirtualSubnet, VirtualSubnetAdmin)
admin.site.register(Cluster, ClusterAdmin)
admin.site.register(ClusterPartition)
admin.site.register(ComputeInstance)
admin.site.register(Credential)
admin.site.register(Job, JobAdmin)
admin.site.register(Benchmark)
admin.site.register(Role)
admin.site.register(User, UserAdmin)
admin.site.register(Filesystem, FilesystemAdmin)
admin.site.register(GCPFilestoreFilesystem)
admin.site.register(FilesystemExport)
admin.site.register(MountPoint)
admin.site.register(Workbench)
admin.site.register(WorkbenchPreset)
admin.site.register(AuthorisedUser)
admin.site.register(WorkbenchMountPoint)
admin.site.register(StartupScript)
admin.site.register(Image)
admin.site.register(MachineType, MachineTypeAdmin)
admin.site.register(MachineTypeFlavour, MachineTypeFlavourAdmin)
admin.site.register(MachineInstance, MachineInstanceAdmin)