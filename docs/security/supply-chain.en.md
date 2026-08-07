# Supply Chain, SBOM, and Attestations

## Implemented controls

### Architecture repository

The `Attested documentation release` workflow:

1. runs `mkdocs build --strict`;
2. packages the static site;
3. generates a SHA-256 checksum;
4. generates an SPDX JSON SBOM for the built content;
5. creates a provenance attestation;
6. creates a signed SBOM attestation;
7. publishes the bundle as an artifact for 90 days.

It runs manually or on `v*` tags.

### Banking Core Mock

The `Attested container release` workflow:

1. runs the test suite;
2. builds the Docker image;
3. exports the image as a compressed archive;
4. generates a SHA-256 checksum;
5. generates an SPDX JSON SBOM for the image;
6. creates provenance and SBOM attestations;
7. publishes the release bundle.

## Permissions

The workflows use explicit minimum permissions:

```yaml
permissions:
  contents: read
  id-token: write
  attestations: write
  artifact-metadata: write
```

The OIDC token is used only during execution to obtain the attestation signature. No persistent private key exists in the repository.

## Verification

Download the artifact and validate its checksum:

```bash
sha256sum -c SHA256SUMS
```

Validate the attestation associated with the artifact:

```bash
gh attestation verify <file> \
  --repo leandrosflora/conversational-ai-platform-architecture
```

For the Core:

```bash
gh attestation verify core-bancario-mock-image.tar.gz \
  --repo leandrosflora/core-bancario-mock
```

Verification must be performed against the original file, without recompression or modification.

## Limitations

- only the architecture repository and Core have attested releases in this change set;
- the remaining services still need equivalent image-by-digest, SBOM, and attestation controls;
- there is no admission controller blocking unattested artifacts;
- the Core's compressed artifact does not replace publication to an enterprise registry;
- production must enforce retention, revocation, and deployment-time policy.
