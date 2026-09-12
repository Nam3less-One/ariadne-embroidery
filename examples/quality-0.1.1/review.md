# Independently reviewed Ariadne 0.1.1 examples

These four original inputs were converted with the final source and reviewed by a separate embroidery critic. Saved PES and DST were reopened, path metrics checked, and comparison screenshots inspected. Scores are digital review, not physical sew-out certification or a promise for arbitrary images.

Setup: 100 mm cropped artwork width, automatic background removal, trim margins enabled, up to four thread colors, 0.42 mm fill spacing, 3 mm running-stitch limit, underlay on. Stable woven fabric and suitable stabilizer assumed. No machine or hoop is specified; use the raw travel dimensions in each review.json.

| Sample | Fidelity / 10 | Digitizing quality / 10 | Actual threads | DST sewing stitches | Trims |
|---|---:|---:|---:|---:|---:|
| [ring-arrow](ring-arrow/design-pes-proof.png) | 8.7 | 8.1 | 1 | 6199 | 17 |
| [botanical](botanical/design-pes-proof.png) | 8.7 | 8.2 | 3 | 9835 | 22 |
| [narrow-monogram](narrow-monogram/design-pes-proof.png) | 8.2 | 8.0 | 1 | 4755 | 17 |
| [grow](grow/design-pes-proof.png) | 8.5 | 8.0 | 3 | 8130 | 44 |

The ring and botanical preserve broad fill, counters and source hues. The narrow mark combines broad fill with explicit satin on its near-perfect straight baseline; this is not automatic general lettering. GROW preserves leaf veins and letter counters, with meaningful green/terracotta/gold colors. Some short edge stitches remain (about 5.8% below 0.2 mm for GROW); review and test sew before production. Cropped GROW is about 100 × 109.9 mm before trim travel, so a nominal 100 × 100 mm hoop is insufficient.

Each sample includes its original image, editable plan, actual machine files, PES/DST decoded proofs, DST needle/travel diagrams and thread chart. PES embeds the planned palette; DST requires threads.json and machine-specific interpretation of three-jump trim requests. review.json retains exact metrics and hashes.

Controlled graphics are original CC0 fixtures. GROW was generated specifically for this test using the prompt in generated-input-prompt.txt; it is not an existing brand or a real stitched photograph. Its transparent background and subtle shade variation were preserved. See provenance.json.

## Exact reviewed machine hashes

- ring-arrow PES SHA-256: `26e471035d906485b287d9e71852a510cf66a349203d7ecc10888f78dcaf7c1d`
- ring-arrow DST SHA-256: `7a6e4bffd7fe8e9a1e3a3ad1a4b107ad08195bb1f81d21a8e216f9257f49ea1e`
- botanical PES SHA-256: `defb1769d3adbff1e918d481b2659f6d8347efdae2197906bcc9127a41f0177b`
- botanical DST SHA-256: `d1486b9361d8eb64071b22a5b7b48dbaacacafa2f98fe300b03b7eb412445bb2`
- narrow-monogram PES SHA-256: `3868e67f4b643bc4532ed7b363318017197855e8b9d96ddfb6d7f7886cc2a29c`
- narrow-monogram DST SHA-256: `82b32ced6b2a608fe3cda8e80f4e0516ca3e7484b694afe1d58a4acea74667d3`
- grow PES SHA-256: `5f16835febfc39a4176718b01b4558824a443cab4da31e79c570dccaff227307`
- grow DST SHA-256: `2a7ff66099404a8aec2edd2931aa0c75407ee946eb9e2b81f5139ea5d8a81050`
