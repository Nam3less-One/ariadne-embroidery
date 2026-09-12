# Independent digital embroidery review: geometric sample v3

**Source fidelity: 8.4/10. Digitizing quality: 8.0/10.** This sample passes the project's digital review threshold. These scores apply only to the exact files below. They do not certify arbitrary converter outputs or predict a physical sew-out.

## Method and evidence

The reviewer independently decoded the PES and DST, rendered actual sewing commands, captured and inspected `browser-screenshot.png`, and inspected the detailed needle and travel views. The DST was additionally decoded directly from its three-byte balanced-ternary records, independently of the library reader. Geometry checks compared sewing segments with the original sample's extracted regions. The fidelity target is the original geometric artwork, not a generated embroidery photograph. No physical sew-out was performed.

## Findings

- The ring, open counter, triangle, rounded bar, spacing and two-color identity are preserved. The 0.4 mm fill pitch gives visibly more consistent coverage in the illustrative proof than v1/v2. Curved edges still show fine faceting; they are credible draft fill edges, not polished satin borders.
- The previous excessive trim count is resolved: nine DST trim sequences across three shapes and their underlay are reasonable for this example. All nonzero transfers after sewing have the expected three-jump trim convention. Actual cutting still depends on controller settings.
- The previous 105 zero-length DST stitches are eliminated. Maximum sewing length is 3.0 mm. Underlay is present and counters are not bridged with sewing stitches. No nonzero sewing segment exceeds the intended source region plus 0.08 mm tolerance.
- All 3,901 DST records are valid; ST matches the body, CO is one, END is last, and header extents now include trim motion. Raw travel is 65.5 x 54.0 mm; needle bounds are 65.3 x 53.8 mm. The artwork canvas is 80 x 66.67 mm, including transparent margins.
- The PES reader reports nine zero-length transitions; the DST has none. PES and DST decoder trim counts differ, so those counts should not be treated as physical cut counts or expected to match.

## Remaining adjustment advice

There are 258 positive stitches shorter than 0.2 mm in the DST, about 6.7% of sewing commands. This is substantially improved from v2 and is not accompanied by duplicate DST penetrations. An additional spatial check found at most 11 penetrations within a 0.5 mm radius around a needle point (99th percentile nine), which does not suggest an isolated severe penetration pileup in this sample. Still, merging short row-end fragments and improving smooth boundary routing would be worthwhile, especially for fragile fabric. Preserve corners and counters when doing so.

Test sew on the intended stable woven fabric and stabilizer. Check ring-edge pull-in, triangle-tip stiffness, trim tails and inter-object registration; adjust compensation or edge treatment from that evidence. The preview uses an illustrative 0.42 mm thread spread and rasterization can show or hide fine row gaps. Neither density coverage nor lack of puckering can be established from a flat rendering. Automatic small lettering and satin planning remain separate limitations of the general converter.

## Exact files reviewed

PES SHA-256: `8d0e7cabfceaca2bf10c9d2bb51ebceecace0839408793ad9e92689ba9730252`

DST SHA-256: `8db1599ba428bfd6ddd75adc30e82b2c6284b01620b9c5d145cf491f1e775cc6`

This report is suitable for public distribution with the original synthetic sample. No private artwork or machine-owner details are included.
