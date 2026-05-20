"""
    Package marker for ``automojo.restclient.vsphere.apigroups``.

    Each ``*Group`` module owns its own class.  This package init does
    not eagerly import the groups; importing happens lazily through
    :meth:`VSphereClient.__getattr__` so the package is cheap to load.
"""
