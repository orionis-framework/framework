from enum import StrEnum

class DiskName(StrEnum):
    """
    Enumerate the built-in filesystem disk names supported by Orionis.

    Attributes
    ----------
    LOCAL : str
        Represents the local private disk.
    PUBLIC : str
        Represents the local public disk.
    S3 : str
        Represents the AWS S3 disk.
    AZURE : str
        Represents the Azure Blob Storage disk.
    GCS : str
        Represents the Google Cloud Storage disk.

    Returns
    -------
    DiskName
        An enumeration member representing a filesystem disk name.
    """

    LOCAL = "local"  # Local private disk
    PUBLIC = "public"  # Local public disk
    S3 = "s3"  # AWS S3 disk
    AZURE = "azure"  # Azure Blob Storage disk
    GCS = "gcs"  # Google Cloud Storage disk
