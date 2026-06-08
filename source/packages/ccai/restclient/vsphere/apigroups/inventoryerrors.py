"""
    .. module:: inventoryerrors
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Inventory-helper exception classes shared across the
        :mod:`apigroups` modules and re-exported from the package root.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import List, Optional


class VSphereResourceNotFoundError(Exception):
    """
        Raised when an inventory helper finds no matching resource.
    """

    def __init__(self, message: str) -> None:
        """
            Initialise the error with a descriptive message.

            :param message: Multi-line error text.

            :returns: ``None``
        """
        super().__init__(message)
        return


class VSphereAmbiguousResolutionError(Exception):
    """
        Raised when a helper that requires uniqueness finds multiple
        matches.  The colliding candidates are attached so callers can
        produce actionable error messages.
    """

    def __init__(
        self,
        message: str,
        candidates: Optional[List[object]] = None,
    ) -> None:
        """
            Initialise the error.

            :param message: Multi-line error text.
            :param candidates: List of colliding candidate records.

            :returns: ``None``
        """
        super().__init__(message)
        if candidates is None:
            self.candidates: List[object] = []
        else:
            self.candidates = list(candidates)
        return
