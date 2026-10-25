# Compatibility reports

Include the distribution, Lutris version, exact Wine build, prefix architecture,
.NET release, ESU version, FTDI vendor/product and driver, programmer model,
decoder model, and the operation you actually tested. State whether it completed,
which errors appeared, whether the UI remained responsive, and whether repeated
reads worked. Separate programmer detection, decoder reading, settings writes,
sound writes and firmware updates.

Do not attach Wine prefixes, installers, licensed sound projects, private project
files, credentials or unreviewed logs. Redact usernames, USB serial numbers,
paths and project names as appropriate. The serial timing log does not need
packet payloads to show deadline behavior.

Run `python -m unittest discover -s tests -v` for setup-script changes. For source
changes, build with the documented .NET compiler and run `--check-wmi`. Hardware
self-tests require the application closed. Do not claim write/firmware support
from a read test, and preserve a known working helper before experiments.
