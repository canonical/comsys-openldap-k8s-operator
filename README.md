# comsys-openldap-k8s-operator
A minimal charm wrapper around the OpenLDAP application for use by the Commercial Systems team with the [Ranger K8s charm](https://github.com/canonical/ranger-k8s-operator).

OpenLDAP is an open source implementation of the Lightweight Directory Access Protocol.


# Deploy OpenLDAP
```
juju deploy comsys-openldap-k8s --channel=edge
```

# LDAP functions
## LDAPSEARCH
Get the unit ip from `juju status`.
Replace the values of the bind 
```
ldapsearch -x -H ldap://{unit-ip}:389 -b {ldap-base-dn} -D "cn={ldap-admin-username},{ldap-base-dn}" -w {ldap-admin-password} -s sub "(objectClass=top)"

## example
ldapsearch -x -H ldap://10.152.183.169:389 -b "dc=canonical,dc=dev,dc=com" -D "cn=admin,dc=canonical,dc=dev,dc=com" -w admin -s sub "(objectClass=top)" 

```

## LDAPADD & LDAPMODIFY
Users, groups and memberships can be added with `.ldif` files. These are setup to work with the example bind dn, please update as needed.

```
# Update the LDAP with your own users and groups
ldapadd -x -H ldap://{unit-ip}:389 -D "cn={ldap-admin-username},{ldap-base-dn}" -w {ldap-admin-password} -f {your file}.ldif 

```
