# Swift Tool

A small command-line utility that renames photo files from their EXIF timestamps.
Swift 5.9, Swift Package Manager, no external services.

Build with `swift build -c release`; the binary lands in `.build/release/`.

Dependencies are vendored into `.build/checkouts/` by SwiftPM. That directory belongs
to the build system: never edit anything inside it, and never commit it.

Tests run with `swift test` and use the sample images in `Tests/Fixtures/`.
