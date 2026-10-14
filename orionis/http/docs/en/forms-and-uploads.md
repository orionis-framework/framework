# Forms and uploaded files

Use `await request.form()` to preserve repeated form fields and uploaded files. The resulting `FormData` can come from URL encoded or multipart input. `get(key)` selects the last value; `getAll(key)` retains all values. `fields` groups text and `files` groups `UploadedFile` objects. `multiItems()` preserves the complete sequence of pairs.

## Inspecting an attachment without retaining temporary files

```python
from orionis.http import Request, response

async def inspect_attachment(request: Request):
    form = await request.form()
    try:
        uploads = form.files.get("attachment", [])
        if len(uploads) != 1:
            return response.json({"message": "One attachment is required"}, 422)
        upload = uploads[0]
        return response.json({
            "filename": upload.filename,
            "size": upload.size,
            "extension": upload.extension,
            "labels": form.getAll("label"),
        })
    finally:
        form.close()
```

The client must send `multipart/form-data` with a valid boundary. This example stores no data and is useful for checking form integration. `FormData` also supports a synchronous context manager: `with await request.form() as form:`. Do not use `async with`; `close()` is synchronous.

## Saving under application control

`UploadedFile.read()` returns bytes, `chunks(size)` iterates blocks and `save(path)` copies to a destination. These methods are synchronous. Avoid writing a large file to slow storage on the event loop without delegating the work. `replace(data)` replaces content; `size` and `extension` are properties. The extension includes its dot and is lowercase.

The incoming name is sanitized to remove separators, controls and leading dots. This does not inspect content or ensure uniqueness. Generate your own storage name, validate bytes and MIME according to your domain, and use an authorized destination. Do not turn a client name directly into a public path. For persistent storage, see [files](../../../storage/docs/en/README.md).

Files start in memory and spill to a temporary file above `HTTP_UPLOAD_MEMORY_THRESHOLD`. Retain only persisted results; a closed `UploadedFile` is no longer a usable source for background work. Persist first and pass a domain identifier or controlled path when processing later.

## Multipart budgets

`config/http.py` declares file (`HTTP_MAX_FILES`), field (`HTTP_MAX_FIELDS`), part (`HTTP_MAX_PART_SIZE`), field-size (`HTTP_MAX_FIELD_SIZE`), header-size (`HTTP_MAX_PART_HEADER_SIZE`), file-spill and total multipart memory (`HTTP_MAX_MULTIPART_MEMORY_SIZE`) limits. They combine with the overall body limit. Raising the total does not remove individual part limits.

Incomplete uploads, invalid boundaries, excessive parts and oversized content produce parsing or limit errors. The parser cleans temporary uploads on failure; handlers must still avoid retaining references or abandoning their own copies. Size temporary storage and memory per worker multiplied by concurrency.


Initial `HTTPBodyLimits` values are:

| Limit | Value |
|---|---:|
| Files / fields | 32 / 128 |
| Individual part | 10 MiB |
| Text field | 1 MiB |
| Part header | 16 KiB |
| In-memory file threshold | 256 KiB |
| Total retained multipart memory | 8 MiB |

Memory budgets exclude some objects, temporary copies and server buffers. Zero files or fields rejects that part kind; it does not mean unlimited.

Evidence: [FormData](../../payload/form_data.py), [UploadedFile](../../payload/uploaded_file.py), [parser](../../payload/stream_parser.py), [configuration](../../../../config/http.py). Tests: [uploads](../../../../tests/http/payload/test_uploaded_file.py), [incremental parser](../../../../tests/http/payload/test_stream_parser.py), [limits](../../../../tests/http/payload/test_body_limits.py). Return to [input](requests-and-validation.md) or continue with [responses](responses.md).
