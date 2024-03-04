# Testing

This project uses `tox` for managing test environments (4.4.x). There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the charm:

```shell
tox run -e format        # update your code according to linting rules
tox run -e lint          # code style
tox run -e unit          # unit tests
tox run -e integration   # integration tests
tox                      # runs 'format', 'lint', and 'unit' environments
```

# Deploy OpenLDAP

This charm is used to deploy OpenLDAP Server in a k8s cluster. For local deployment, follow the following steps:

## Set up your development environment with Multipass [~ 10 mins]
When you’re trying things out, it’s good to be in an isolated environment, so you don’t have to worry too much about cleanup. It’s also nice if you don’t need to bother too much with setup. In the Juju world you can get both by spinning up an Ubuntu virtual machine (VM) with Multipass, specifically, using their Juju-ready `charm-dev` blueprint.
```
sudo snap install multipass
multipass launch --cpus 4 --memory 8G --disk 30G --name openldap-vm charm-dev
```
That's it! Your dependencies are all set up, please run `multipass shell openldap-vm` and skip to `Create a model`.

## Set up your development environment without Multipass blueprint
### Install Microk8s
```
# Install microk8s from snap:
sudo snap install microk8s --channel=1.27-strict/stable

# Setup an alias for kubectl:
sudo snap alias microk8s.kubectl kubectl

# Add your user to the Microk8s group:
sudo usermod -a -G snap_microk8s $USER

# Switch to the 'microk8s' group:
newgrp snap_microk8s

# Wait for microk8s to be ready:
microk8s status --wait-ready

# Enable the necessary Microk8s addons:
sudo microk8s.enable dns 
sudo microk8s.enable rbac 
sudo microk8s.enable hostpath-storage

# Wait for addons to be rolled out:
microk8s.kubectl rollout status deployments/coredns -n kube-system -w --timeout=600s
microk8s.kubectl rollout status deployments/hostpath-provisioner -n kube-system -w --timeout=600s
```
### Install Charmcraft
```
# Install lxd from snap:
sudo snap install lxd --classic --channel=5.0/stable

# Install charmcraft from snap:
sudo snap install charmcraft --classic --channel=latest/stable

# Charmcraft relies on LXD. Configure LXD:
lxd init --auto
```
### Set up the Juju OLM
```
# Install the Juju CLI client, juju:
sudo snap install juju --channel=3.1/stable

# Make Juju directory
mkdir -p ~/.local/share/juju

# Install a "juju" controller into your "microk8s" cloud:
juju bootstrap microk8s openldap-controller
```
### Create a model
```
# Create a 'model' on this controller:
juju add-model openldap-k8s

# Enable DEBUG logging:
juju model-config logging-config="<root>=INFO;unit=DEBUG"

# Check progress:
juju status
juju debug-log
```
### Deploy charm
```
# Copy the repository
git clone https://github.com/canonical/comsys-openldap-k8s-operator.git
cd comsys-openldap-k8s-operator

# Pack the charm:
charmcraft pack

# deploy the web server
juju deploy ./openldap-k8s_ubuntu-22.04-amd64.charm --resource openldap-image=osixia/openldap:1.5.0 openldap-k8s

# Check deployment was successful:
juju status
```
## Relations
There are currently no supported relations. Set the binddn and other parameters using `juju config openldap-k8s <key>=<value>`


```

## Cleanup
# Remove the application before retrying
```
juju remove-application superset-k8s-ui superset-k8s-beat superset-k8s-worker --force
```