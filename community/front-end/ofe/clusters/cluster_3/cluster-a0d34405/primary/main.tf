/**
  * Copyright 2023 Google LLC
  *
  * Licensed under the Apache License, Version 2.0 (the "License");
  * you may not use this file except in compliance with the License.
  * You may obtain a copy of the License at
  *
  *      http://www.apache.org/licenses/LICENSE-2.0
  *
  * Unless required by applicable law or agreed to in writing, software
  * distributed under the License is distributed on an "AS IS" BASIS,
  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  * See the License for the specific language governing permissions and
  * limitations under the License.
  */

module "hpc_network" {
  source          = "./modules/embedded/modules/network/pre-existing-vpc"
  network_name    = "legible-polliwog-network"
  project_id      = var.project_id
  region          = var.region
  subnetwork_name = "legible-polliwog-subnet-2"
}

module "mount_num_0" {
  source        = "./modules/embedded/modules/file-system/pre-existing-network-storage"
  fs_type       = "nfs"
  local_mount   = "/opt/cluster"
  mount_options = "defaults,nofail,nosuid"
  remote_mount  = "/opt/cluster"
  server_ip     = "$controller"
}

module "mount_num_1" {
  source        = "./modules/embedded/modules/file-system/pre-existing-network-storage"
  fs_type       = "nfs"
  local_mount   = "/home"
  mount_options = "defaults,nofail,nosuid"
  remote_mount  = "/home"
  server_ip     = "$controller"
}

module "hpc_service_account" {
  source          = "./modules/embedded/community/modules/project/service-account"
  deployment_name = var.deployment_name
  name            = "sa"
  project_id      = "eimantask-personal-project"
  project_roles   = ["compute.instanceAdmin.v1", "iam.serviceAccountUser", "monitoring.metricWriter", "logging.logWriter", "storage.objectAdmin", "pubsub.admin", "compute.securityAdmin", "iam.serviceAccountAdmin", "resourcemanager.projectIamAdmin", "compute.networkAdmin"]
}

module "partition_0" {
  source               = "./modules/embedded/community/modules/compute/schedmd-slurm-gcp-v5-partition"
  deployment_name      = var.deployment_name
  enable_placement     = false
  enable_reconfigure   = var.enable_reconfigure
  exclusive            = false
  network_storage      = flatten([module.mount_num_1.network_storage, flatten([module.mount_num_0.network_storage])])
  node_groups          = flatten([module.partition_0-group.node_groups])
  partition_name       = "batch"
  project_id           = var.project_id
  region               = var.region
  subnetwork_self_link = "legible-polliwog-subnet-2"
  zone                 = var.zone
}

module "partition_0-group" {
  source                 = "./modules/embedded/community/modules/compute/schedmd-slurm-gcp-v5-node-group"
  disk_size_gb           = 50
  disk_type              = "pd-standard"
  enable_smt             = false
  instance_image_custom  = var.instance_image_custom
  labels                 = var.labels
  machine_type           = "c2-standard-60"
  node_count_dynamic_max = 4
  node_count_static      = 0
  project_id             = var.project_id
}

module "slurm_controller" {
  source = "./modules/embedded/community/modules/scheduler/schedmd-slurm-gcp-v5-controller"
  cloud_parameters = {
    no_comma_params = false
    resume_rate     = 0
    resume_timeout  = 500
    suspend_rate    = 0
    suspend_timeout = 300
  }
  compute_startup_script             = "#!/bin/bash\ngsutil cp gs://aicluster-storage-08c2/clusters/3/bootstrap_compute.sh - | bash\n"
  compute_startup_scripts_timeout    = 900
  controller_startup_script          = "#!/bin/bash\necho \"******************************************** CALLING CONTROLLER STARTUP\"\ngsutil cp gs://aicluster-storage-08c2/clusters/3/bootstrap_controller.sh - | bash\n"
  controller_startup_scripts_timeout = 900
  deployment_name                    = var.deployment_name
  disk_size_gb                       = 50
  disk_type                          = "pd-standard"
  enable_bigquery_load               = var.enable_bigquery_load
  enable_cleanup_compute             = var.enable_cleanup_compute
  enable_cleanup_subscriptions       = var.enable_cleanup_subscriptions
  enable_reconfigure                 = var.enable_reconfigure
  instance_image_custom              = var.instance_image_custom
  labels                             = var.labels
  machine_type                       = "n2-standard-2"
  network_self_link                  = module.hpc_network.network_self_link
  network_storage                    = flatten([module.mount_num_1.network_storage, flatten([module.mount_num_0.network_storage])])
  partition                          = flatten([module.partition_0.partition])
  project_id                         = var.project_id
  region                             = var.region
  service_account = {
    email  = module.hpc_service_account.service_account_email
    scopes = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/devstorage.read_write", "https://www.googleapis.com/auth/pubsub"]
  }
  subnetwork_self_link = module.hpc_network.subnetwork_self_link
  zone                 = var.zone
}

module "slurm_login" {
  source                 = "./modules/embedded/community/modules/scheduler/schedmd-slurm-gcp-v5-login"
  controller_instance_id = module.slurm_controller.controller_instance_id
  deployment_name        = var.deployment_name
  disk_size_gb           = 50
  disk_type              = "pd-standard"
  enable_reconfigure     = var.enable_reconfigure
  instance_image_custom  = var.instance_image_custom
  labels                 = var.labels
  machine_type           = "n2-standard-2"
  network_self_link      = module.hpc_network.network_self_link
  num_instances          = 1
  project_id             = var.project_id
  pubsub_topic           = module.slurm_controller.pubsub_topic
  region                 = var.region
  service_account = {
    email  = module.hpc_service_account.service_account_email
    scopes = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/devstorage.read_write"]
  }
  startup_script       = "#!/bin/bash\necho \"******************************************** CALLING LOGIN STARTUP\"\ngsutil cp gs://aicluster-storage-08c2/clusters/3/bootstrap_login.sh - | bash\n"
  subnetwork_self_link = "legible-polliwog-subnet-2"
  zone                 = var.zone
}
