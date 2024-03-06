# comsys-openldap-k8s-operator
A minimal charm wrapper around the OpenLDAP application for use by the Commercial Systems team with the [Ranger K8s charm](https://github.com/canonical/ranger-k8s-operator).

OpenLDAP is an open source implementation of the Lightweight Directory Access Protocol.


# Deploy OpenLDAP
```
juju deploy comsys-openldap-k8s --channel=edge
```

# Load test users
Initially the LDAP is empty on deployment, in order to load some users/groups for testing this can be done either with the `ldapadd` action described below or via a `juju action` as described here:
```
# To load some pre-configured test users
juju run comsys-openldap-k8s/0 load-test-users

# To load custom test users from a provided file.
juju run comsys-openldap-k8s/0 load-test-users --params path/to-file.yaml

# example file content
ldif: |
  dn: ou=People,dc=canonical,dc=dev,dc=com
  objectClass: organizationalUnit
  ou: People

  dn: ou=Groups,dc=canonical,dc=dev,dc=com
  objectClass: organizationalUnit
  ou: Groups
  ...
```
Note: this is provided for convenience on deployment. But user management should be handled after this using the ldap functions outlined below.

# LDAP functions
## LDAPSEARCH
Get the unit ip from `juju status`.
Replace the values of the bind 
```
sudo apt install ldap-utils
ldapsearch -x -H ldap://{unit-ip}:389 -b {ldap-base-dn} -D "cn={ldap-admin-username},{ldap-base-dn}" -w {ldap-admin-password} -s sub "(objectClass=top)"

## example
ldapsearch -x -H ldap://10.152.183.169:389 -b "dc=canonical,dc=dev,dc=com" -D "cn=admin,dc=canonical,dc=dev,dc=com" -w admin -s sub "(objectClass=top)" 

```

## LDAPADD & LDAPMODIFY
Users, groups and memberships can be added with `.ldif` files. These are setup to work with the example bind dn, please update as needed. An example is provided in `/templates/startup.ldif`.

```
# Update the LDAP with your own users and groups
ldapadd -x -H ldap://{unit-ip}:389 -D "cn={ldap-admin-username},{ldap-base-dn}" -w {ldap-admin-password} -f {your file}.ldif 

```
