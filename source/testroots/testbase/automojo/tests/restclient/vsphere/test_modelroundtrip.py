"""
    Tests for the typed DTO / spec round-trip behaviour
    (``from_dict(to_dict(x)) == x``).  Includes hypothesis-based
    coverage on three representative model classes.
"""

import unittest

from hypothesis import given, settings, strategies as st

from automojo.restclient.vsphere.model.summary import (
    ClusterSummary,
    DatacenterSummary,
    FolderSummary,
    HostSummary,
)
from automojo.restclient.vsphere.model.vm import (
    VirtualMachineInfo,
    VirtualMachineSummary,
)
from automojo.restclient.vsphere.model.network import (
    NetworkSummary,
    DistributedSwitchSummary,
)
from automojo.restclient.vsphere.model.datastore import (
    DatastoreInfo,
    DatastoreSummary,
)
from automojo.restclient.vsphere.model.ovf import (
    OvfDescriptor,
    OvfDeployResult,
)
from automojo.restclient.vsphere.model.event import EventRecord
from automojo.restclient.vsphere.specs.vmcreate import VmCreateSpec
from automojo.restclient.vsphere.specs.vmclone import VmCloneSpec
from automojo.restclient.vsphere.specs.vmsnapshot import VmSnapshotSpec
from automojo.restclient.vsphere.specs.vmpoweraction import VmPowerActionSpec
from automojo.restclient.vsphere.specs.vmguestcustomization import VmGuestCustomizationSpec


class TestModelRoundTrip(unittest.TestCase):

    def test_datacentersummary_roundtrip(self) -> None:
        src = DatacenterSummary(name="dc-name", datacenter="dc-1")
        rebuilt = DatacenterSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_foldersummary_roundtrip(self) -> None:
        src = FolderSummary(name="folder-name", folder="folder-1", type="VIRTUAL_MACHINE")
        rebuilt = FolderSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_clustersummary_roundtrip(self) -> None:
        src = ClusterSummary(name="c1", cluster="cluster-1", ha_enabled=True, drs_enabled=False)
        rebuilt = ClusterSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_hostsummary_roundtrip(self) -> None:
        src = HostSummary(name="h1", host="host-1", connection_state="CONNECTED", power_state="POWERED_ON")
        rebuilt = HostSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_vmsummary_roundtrip(self) -> None:
        src = VirtualMachineSummary(name="vm1", vm="vm-1", power_state="POWERED_ON", cpu_count=4, memory_size_MiB=2048)
        rebuilt = VirtualMachineSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_networksummary_roundtrip(self) -> None:
        src = NetworkSummary(name="vmnet", network="net-1", type="STANDARD_PORTGROUP")
        rebuilt = NetworkSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_dvsummary_roundtrip(self) -> None:
        src = DistributedSwitchSummary(name="dvs", switch="dvs-1", uuid="uuid", version="8.0")
        rebuilt = DistributedSwitchSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_datastoresummary_roundtrip(self) -> None:
        src = DatastoreSummary(name="ds", datastore="datastore-1", type="VMFS", capacity=100, free_space=10)
        rebuilt = DatastoreSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_datastoreinfo_roundtrip(self) -> None:
        src = DatastoreInfo(
            name="ds", datastore="datastore-1", type="VMFS",
            capacity=100, free_space=10,
            accessible=True, multiple_host_access=False,
            thin_provisioning_supported=True,
        )
        rebuilt = DatastoreInfo.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_ovfdescriptor_roundtrip(self) -> None:
        src = OvfDescriptor(name="appliance", vendor="ACME", version="1.0", eula=[], properties=[], networks=[])
        rebuilt = OvfDescriptor.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_ovfdeployresult_roundtrip(self) -> None:
        src = OvfDeployResult(resource_id="r-1", deployable=True, error=None)
        rebuilt = OvfDeployResult.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_eventrecord_roundtrip(self) -> None:
        src = EventRecord(id="e-1", type="VmCreated", timestamp="2026-01-01T00:00:00Z",
                          severity="INFO", message="created", user="root", target={})
        rebuilt = EventRecord.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_vmcreatespec_roundtrip(self) -> None:
        src = VmCreateSpec(name="vm-new", guest_OS="UBUNTU_64", placement={}, hardware={}, storage={}, networks=[])
        rebuilt = VmCreateSpec.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_vmclonespec_roundtrip(self) -> None:
        src = VmCloneSpec(source_vm_id="vm-1", target_name="vm-1-clone", placement={}, power_on_after=False, customization_spec_ref=None)
        rebuilt = VmCloneSpec.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_vmsnapshotspec_roundtrip(self) -> None:
        src = VmSnapshotSpec(name="snap1", description="d", memory=True, quiesce=False)
        rebuilt = VmSnapshotSpec.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_vmpoweractionspec_roundtrip(self) -> None:
        src = VmPowerActionSpec(action="POWER_ON")
        rebuilt = VmPowerActionSpec.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    def test_vmguestcustomizationspec_roundtrip(self) -> None:
        src = VmGuestCustomizationSpec(
            hostname="host", dns_servers=["1.1.1.1"], dns_search=["example.com"],
            network_configs=[], ssh_authorized_keys=[], run_command_scripts=[],
        )
        rebuilt = VmGuestCustomizationSpec.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return


# ---------------------------------------------------------------------
# Property-based round-trip on three representative models
# ---------------------------------------------------------------------


_name = st.text(min_size=1, max_size=20).filter(lambda s: "\x00" not in s)


class TestModelRoundTripProperties(unittest.TestCase):

    @settings(max_examples=50, deadline=None)
    @given(_name, _name, st.integers(min_value=0, max_value=512), st.integers(min_value=128, max_value=65536))
    def test_vmsummary_property(self, name, vm_id, cpu_count, mem_mib) -> None:
        src = VirtualMachineSummary(name=name, vm=vm_id, power_state="POWERED_OFF", cpu_count=cpu_count, memory_size_MiB=mem_mib)
        rebuilt = VirtualMachineSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    @settings(max_examples=50, deadline=None)
    @given(_name, _name)
    def test_datacentersummary_property(self, name, dc_id) -> None:
        src = DatacenterSummary(name=name, datacenter=dc_id)
        rebuilt = DatacenterSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return

    @settings(max_examples=50, deadline=None)
    @given(_name, _name, st.integers(min_value=0, max_value=10**12), st.integers(min_value=0, max_value=10**12))
    def test_datastoresummary_property(self, name, ds_id, cap, free) -> None:
        src = DatastoreSummary(name=name, datastore=ds_id, type="VMFS", capacity=cap, free_space=free)
        rebuilt = DatastoreSummary.from_dict(src.to_dict())
        self.assertEqual(src, rebuilt)
        return


if __name__ == "__main__":
    unittest.main()
