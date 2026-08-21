from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.filesystems import (
    GCS, S3, Azure, DiskName, Disks, Filesystems, Local, Public,
)
from orionis.environment import Env

@dataclass(frozen=True, kw_only=True)
class BootstrapFilesystems(Filesystems):

    # ----------------------------------------------------------------------------------
    # default : DiskName | str, optional
    # --- Sets the default filesystem disk name.
    # --- Uses 'FILESYSTEM_DISK' env var or 'DiskName.LOCAL' if not set.
    # ----------------------------------------------------------------------------------

    default: DiskName | str = field(
        default_factory=lambda: Env.get("FILESYSTEM_DISK", DiskName.LOCAL),
    )

    # ----------------------------------------------------------------------------------
    # disks : Disks | dict, optional
    # --- Holds available filesystem disks for the app.
    # --- Defaults to Disks with local, public, and AWS S3 configs.
    # ----------------------------------------------------------------------------------

    disks: Disks | dict = field(
        default_factory=lambda: Disks(

            # --------------------------------------------------------------------------
            # --- Local disk stores files in 'storage/app/private'.
            # --- Uses Local entity for private file storage path.
            # --- Defaults to 'storage/app/private' if not set.
            # --------------------------------------------------------------------------
            local=Local(
                path=Env.get("LOCAL_PATH", "storage/app/private"),
            ),

            # --------------------------------------------------------------------------
            # --- Public disk stores files in 'storage/app/public'.
            # --- Uses Public entity for storage path and public URL.
            # --- Defaults to 'storage/app/public' and serves from '/static'.
            # --------------------------------------------------------------------------
            public=Public(
                path=Env.get("PUBLIC_PATH", "storage/app/public"),
                url=Env.get("PUBLIC_URL", "/static"),
            ),

            # --------------------------------------------------------------------------
            # --- AWS S3 disk uses S3 entity for cloud storage.
            # --- Defaults to empty credentials and 'us-east-1' region.
            # --- Path style endpoint is disabled by default.
            # --- Requires the official AWS SDK (optional dependency):
            # ---   pip install boto3   (or: pip install orionis[s3])
            # --------------------------------------------------------------------------
            s3=S3(
                key=Env.get("S3_KEY", ""),
                secret=Env.get("S3_SECRET", ""),
                region=Env.get("S3_REGION", "us-east-1"),
                bucket=Env.get("S3_BUCKET", ""),
                url=Env.get("S3_URL", None),
                endpoint=Env.get("S3_ENDPOINT", None),
                use_path_style_endpoint=Env.get("S3_USE_PATH_STYLE_ENDPOINT", False),
            ),

            # --------------------------------------------------------------------------
            # --- Azure disk uses Azure entity for Blob Storage.
            # --- Authenticate with a connection string or account name/key.
            # --- Requires the official Azure SDK (optional dependency):
            # ---   pip install azure-storage-blob   (or: pip install orionis[azure])
            # --------------------------------------------------------------------------
            azure=Azure(
                connection_string=Env.get("AZURE_CONNECTION_STRING", ""),
                account_name=Env.get("AZURE_ACCOUNT_NAME", ""),
                account_key=Env.get("AZURE_ACCOUNT_KEY", ""),
                container=Env.get("AZURE_CONTAINER", ""),
                url=Env.get("AZURE_URL", None),
            ),

            # --------------------------------------------------------------------------
            # --- GCS disk uses GCS entity for Google Cloud Storage.
            # --- Uses the key file or Application Default Credentials.
            # --- Requires the official Google SDK (optional dependency):
            # ---   pip install google-cloud-storage  (or: pip install orionis[gcs])
            # --------------------------------------------------------------------------
            gcs=GCS(
                project_id=Env.get("GCS_PROJECT_ID", ""),
                key_file=Env.get("GCS_KEY_FILE", None),
                bucket=Env.get("GCS_BUCKET", ""),
                url=Env.get("GCS_URL", None),
            ),

        ),
    )
