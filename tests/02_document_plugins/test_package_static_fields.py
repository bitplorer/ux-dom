"""``PackageStaticContribution`` carries no fields that nothing reads."""

import dataclasses

from ux_dom.plugins.package_static import PackageStaticContribution


def test_no_dead_mount_fields():
    names = {f.name for f in dataclasses.fields(PackageStaticContribution)}
    assert not names & {"mount_package", "mount_subdir"}
