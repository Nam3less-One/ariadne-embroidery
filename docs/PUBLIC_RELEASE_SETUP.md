# Selected public distribution

Use GitHub Free and a public repository named `ariadne-embroidery`, initially owned by the maintainer's personal account. Default branch: `main`. Description: “Free offline embroidery drafting for small businesses: editable plans, PES/DST export and decoded proofs.”

Publish the source folder as the repository root. Do not upload its parent studio workspace. Preserve the MIT license and dependency notices. Public downloads use GitHub Releases, with the Windows installer and small-business guide linked prominently from the README. Distribution remains early access and carries no production certification.

No payment or email gate is part of Ariadne. A paid GitHub subscription, custom domain, commercial AI API and additional hosting account are unnecessary for this configuration. Current platform documentation: [GitHub Free](https://docs.github.com/en/get-started/learning-about-github/githubs-plans), [Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Before publishing

Authenticate as the intended owner. For an existing repository, update its reviewed source. Run the provided CI workflow and attach the exact installer, source ZIP, wheel, sdist and checksums to a draft release. Preserve early-access language and identify which checks were performed.

After publication, verify the download and README while signed out. Record the actual public URL and source commit; do not invent an owner or assume a locally prepared repository is online. See [release instructions](RELEASING.md).

SourceForge can be considered later as a mirror. Itch.io is optional; use its “No payments” option if added. PyPI is a developer channel for later publication. Codeberg is not selected because its [July 2026 policy announcement](https://blog.codeberg.org/protecting-our-floss-commons-from-llms.html) raises a mismatch with this project's heavy agent-assisted development.
