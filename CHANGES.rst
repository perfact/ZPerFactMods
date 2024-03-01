22.1.0+nmu1
======

- Allow ``perfact.mfa``

22.1.0
======

- Allow ``perfact.http_protocol``
- Change versioning to be based on new template versioning scheme

4.3.1
=====
- Allow module cbor2.decoder

4.3.0
=====
- Prevent application error in protected URLs for objects that do not implement
  ``isTopLevelPrincipiaApplicationObject``.

4.2.0
=====
- Add automatic calling of request_init/request_end to wrap each request

4.1.0
=====

- Do not throw errors in protectedURLs if a builtin object of Zope is to be
  served that has no title property.
