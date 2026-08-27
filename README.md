# T3 Code Nightly for Nix

An automatically updated, reproducible Nix package for the official T3 Code
nightly Linux AppImage.

The updater runs every six hours. It accepts only prerelease tags shaped like
`vX.Y.Z-nightly.YYYYMMDD.BUILD` that include the matching x86_64 AppImage,
updates the fixed-output hash, builds the package, and commits the pin only
after the build succeeds.

## Use

```nix
{
  inputs.t3code-nightly-nix.url = "github:crowquillx/t3code-nightly-nix";
}
```

The package is available as:

```nix
inputs.t3code-nightly-nix.packages.x86_64-linux.t3code-nightly
```

## Update manually

```bash
python3 scripts/update.py
nix flake check
```

## Cache retention

Successful updater runs move the Cachix pin named `latest` with
`--keep-revisions 1`. Only the newest revision remains protected from garbage
collection. Cachix reclaims older unpinned store paths using its normal
least-recently-used garbage collection policy.
