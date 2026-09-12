# Selected public distribution

Use GitHub Free and a public repository named `ariadne-embroidery`, initially owned by the maintainer's personal account. Default branch: `main`. Description: “Free offline embroidery drafting for small businesses: editable plans, PES/DST export and decoded proofs.”

Publish the source folder as the repository root. Do not upload its parent studio workspace. Preserve the MIT license and dependency notices. Public downloads should use GitHub Releases, with the small-business guide linked prominently from the README. The initial package is an early-access source release, not a standalone installer or production certification.

No payment or email gate is part of Ariadne. A paid GitHub subscription, custom domain, commercial AI API and additional hosting account are unnecessary for this configuration. Current platform documentation: [GitHub Free](https://docs.github.com/en/get-started/learning-about-github/githubs-plans), [Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Before publishing

Authenticate as the intended owner. Create the public repository without generating another README or license, because these are already present locally. Push the source, run the provided CI workflow, and attach the exact release ZIP, wheel, sdist and checksums to a draft release. Preserve early-access language and outstanding physical/desktop checks.

After publication, verify the download and README while signed out. Record the actual public URL and source commit; do not invent an owner or assume a locally prepared repository is online. See [release instructions](RELEASING.md).

SourceForge can be considered later as a mirror. Itch.io is optional; use its “No payments” option if added. PyPI is a developer channel for later publication. Codeberg is not selected because its [July 2026 policy announcement](https://blog.codeberg.org/protecting-our-floss-commons-from-llms.html) raises a mismatch with this project's heavy agent-assisted development.
