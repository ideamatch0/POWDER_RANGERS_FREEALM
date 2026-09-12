"""Editable business-report content. Source facts and proposal assumptions are separated."""
from business_model import model
M=model()
S={
'1':('Interspectral — AM Explorer platform','https://interspectral.com/solutions-am-explorer/am-explorer-platform/'),
'2':('Materialise — Quality & Process Control','https://www.materialise.com/en/industrial/software/quality-process-control'),
'3':('EOS — Smart Monitoring public store offer','https://store.eos.info/products/eos-smart-monitoring-software'),
'4':('Additive Assurance — AMiRIS products','https://www.additiveassurance.com/product.html'),
'5':('Additive Assurance — monitoring technology','https://www.additiveassurance.com/technology.html'),
'6':('Renishaw — LPBF software portfolio','https://www.renishaw.com/en/software-for-laser-powder-bed-fusion-metal-3d-printing-systems--15255'),
'7':('Renishaw — InfiniAM Central','https://www.renishaw.com/en/infiniam-central--39816'),
'8':('NIST — real-time AM monitoring metrology','https://www.nist.gov/programs-projects/metrology-real-time-monitoring-additive-manufacturing'),
'9':('NIST — in-situ / ex-situ registration and metadata','https://www.nist.gov/publications/additive-manufacturing-situ-and-ex-situ-data-registration-and-metadata-definition'),
'10':('NIST — process monitoring and NDE, IR 8538','https://www.nist.gov/publications/process-monitoring-and-non-destructive-evaluation-metal-additive-manufacturing'),
'11':('European Commission — CRA reporting obligations','https://digital-strategy.ec.europa.eu/en/policies/cra-reporting'),
'12':('European Commission — CRA legal summary','https://digital-strategy.ec.europa.eu/en/policies/cra-summary'),
'13':('USPTO — comprehensive trademark clearance','https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks'),
'14':('USPTO — likelihood of confusion','https://www.uspto.gov/trademarks/search/likelihood-confusion'),
'15':('FTC — CAN-SPAM compliance guide','https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business'),
'16':('CNIL — commercial email prospecting','https://www.cnil.fr/la-prospection-commerciale-par-courrier-electronique'),
'17':('Formnext — visitor information','https://formnext.mesago.com/frankfurt/en/expo/visitor-information.html'),
'18':('NIST — 3D Scan Strategies dataset','https://doi.org/10.18434/M32044'),
'19':('NIST — open-data licence','https://www.nist.gov/open/license'),
'20':('Aalto — public powder-bed image dataset','https://doi.org/10.5281/zenodo.14996806'),
'21':('Interspectral — onboarding product description, July 2025','https://interspectral.com/wp-content/uploads/AMExplorer-ProductDescription-20250707-screen.pdf'),
'22':('ISO — ISO/ASTM 52920:2023 overview','https://www.iso.org/cms/%20render/live/en/sites/isoorg/contents/data/standard/07/69/76911.html'),
}
def ref(n):
    title,url=S[str(n)];return f'<link href="{url}" color="#166a87">[{n}] {title}</link>'
def P(t):return ('p',t)
def H(t):return ('h',t)
def C(t):return ('c',t)
def B(*items):return ('b',items)
def T(headers,rows,widths=None):return ('t',(headers,rows,widths))
def I(path,caption):return ('i',(path,caption))
pages=[]
def page(title,lead,*blocks):pages.append({'title':title,'lead':lead,'blocks':blocks})

page('The decision: sell an assisted pilot first',
 'Global ambition. A narrow first offer. Evidence before scale.',
 P('<b>Recommendation:</b> develop Powder Ranger into locally deployed, annually licensed image-review software, sold first through a six-week paid pilot. Target industrial LPBF teams that already export layer photographs and spend measurable engineering time reviewing them. Start founder-led, with a small number of technically compatible customers; add partners after repeatable onboarding is demonstrated.'),
 P('The immediate product is a review aid: it surfaces visual changes, supports contextual inspection and records retained observations. Its initial calibration is internal to one job. It does not establish material conformity, reconstruct internal porosity or replace the customer’s qualification process. The reference-job comparison mode is not yet implemented.'),
 T(['Decision','Working recommendation'],[
 ['First customer','An LPBF service bureau or process-development team with accessible raw images, a named reviewer and at least several hours of recurring manual review.'],
 ['First paid offer','€3,000 bounded pilot; then test €6,000/year for one local workstation, with explicit onboarding and support scope. These are pricing hypotheses.'],
 ['First proof','Repeatable time savings on independently held-out jobs, acceptable missed-visible-event review, and stable operation on the agreed PC.'],
 ['First boundary','Supervised pilot only until persistence consistency, source provenance and deployment acceptance gates are resolved.']],[.24,.76]),
 H('What to do immediately'),
 B('Assign an owner to the open P1 audit findings; freeze a versioned pilot build and fixed source copies.',
   'Interview 10 qualified teams before committing to a permanent licence model. Ask for one real workflow and a timed manual-review baseline.',
   'Secure 2–3 design partners, agree a paid scope and a no-material-release interpretation, and measure delivery hours from the first import.'),
 C('Decision gate: proceed to recurring sales only when the product saves useful review time, the customer trusts the evidence trail, and delivery economics work. A polished video is a demonstration asset, not validation.'))

page('Product truth: what can be sold today',
 'Describe verified behavior, experimental visualizations and future work separately.',
 T(['Capability','Current state and commercial interpretation'],[
 ['Single-job analysis','Implemented: internal gray calibration, temporal change/drift, tiled measurements, stage/camera separation where metadata identifies them. No trained model is required.'],
 ['Review workflow','Implemented: shared dark workspace, matching before/peak/after crops, retain/dismiss and automatic advance, adjustable persistence and layer/priority order.'],
 ['Priority score','Implemented: 0–100 review index combining threshold-relative variation and persistence. It is not a calibrated probability or material-severity measurement.'],
 ['3D and reports','Implemented/experimental: photographic stack, approximate cyan post-melting sections, retained markers, three offline HTML report templates and browser PDF printing.'],
 ['Aalto libraries','Three distinct jobs, 2,638 raw images in total. Researcher labels are separate from single-job detection. Unknown physical stage/height must stay unknown.'],
 ['Windows distribution','Self-contained executable is built and tested headlessly. Interactive clean-machine install/update acceptance and code signing remain release gates.'],
 ['Not available','Reference comparison, CAD registration, multi-camera stitching, material-quality certification, closed-loop control, multi-user enterprise service and licence activation.']],[.24,.76]),
 P('User-specific jobs normally use 60 µm layers, but public datasets have their own documented spacing; the NIST video example uses 20 µm. A single hardcoded layer height would create false geometry. Missing or ambiguous identifiers must be visible before analysis.'),
 C('The demonstration uses public data and operator-retained observations. Do not describe those decisions as validated defects or use them to imply detection accuracy.'),
 P('Evidence basis: local source inspection, regression tests and actual report/image renders. Public-data provenance: '+ref(18)+'; '+ref(20)+'.'))

page('Market map: substantial products already exist',
 'Powder Ranger enters an established monitoring and analytics category.',
 T(['Alternative','Vendor-stated scope','Implication for Powder Ranger'],[
 ['Interspectral AM Explorer','QUALIFY: data fusion, 3D, analytics, reporting. DETECT adds GPU-assisted AI. MONITOR adds live dashboards and APIs; machine availability varies.','Closest broad software comparator. A clear small-team workflow and lower onboarding burden must be demonstrated. [1]'],
 ['Materialise QPC','Layer-image analysis, 3D visualization and correlation of process, material, machine and test data.','Competes on connected quality/process evidence. Avoid claiming 3D layer analysis as unique. [2]'],
 ['EOS Smart Monitoring','Machine-specific OT hardware/software, Smart Fusion power correction and training.','A much wider in-situ hardware/software bundle; not a like-for-like JPEG desktop benchmark. [3]'],
 ['Additive Assurance AMiRIS','Monitoring sensor/software products and near-infrared measurement technology.','Targets additional process observability requiring suitable hardware; complement rather than imitate sensor capability. [4,5]'],
 ['Renishaw InfiniAM','Layer images, spectral process information, 2D/3D analysis and a broader machine/data ecosystem.','Native integration and machine context are advantages that an independent importer must earn. [6,7]'],
 ['Manual review / internal scripts','Customer’s current viewer, spreadsheets, image-processing scripts and engineer judgement.','Often the first competitor. Measure actual inconvenience and switching cost before discussing enterprise platforms.']],[.23,.40,.37]),
 P('Vendor pages establish advertised availability, not independent sensitivity, precision or customer return on investment. Exact machine compatibility, deployment terms and current quotations should be obtained during competitive interviews.'),
 P(ref(1)+' · '+ref(2)+' · '+ref(3)+' · '+ref(4)+' · '+ref(5)+' · '+ref(6)+' · '+ref(7)))

page('A defensible entry point',
 'Win a specific workflow instead of promising a universal quality platform.',
 P('Proposed positioning: <b>“Turn existing powder-bed images into a focused, traceable review — locally.”</b> This is a hypothesis to test with customers. “Offline”, “3D” and “machine-independent” are not sufficient differentiators by themselves; established providers already advertise broad analysis workflows.'),
 H('The first value proposition'),
 B('Use exported photographs without adding sensors, where export rights and usable metadata exist.',
   'Explain a flag through matching local crops, visible intensity change and persistence; let the reviewer decide.',
   'Keep customer imagery on the workstation for routine analysis and export a readable, self-contained evidence report.',
   'Offer a short, bounded onboarding experience with an honest compatibility checklist and measured processing limits.'),
 H('What could become difficult to copy'),
 P('Build documented machine/export adapters, validated handling of difficult illumination and camera drift, an excellent review workflow, and an independently evaluated corpus of visible phenomena. Customer data enters a shared research corpus only under a separate, explicit agreement. Default ownership and control remain with the customer; support access is not permission to train, publish or reuse images.'),
 H('Price context, carefully bounded'),
 P('The EOS EU store displayed €27,000 per machine/year for the selected M 290 Smart Monitoring offer on 9 September 2026, with a two-year minimum and an active Build/Build+ plan requirement. Its hardware, control technology and training make it an unsuitable direct price anchor for Powder Ranger. Verify quotation details, taxes and eligibility before comparison. '+ref(3)),
 P('No verified comparable public price was established for the other products in this review. Avoid invented competitor quotations and percentage-cheaper claims. Interspectral’s published onboarding material also supports the inference that implementation assistance matters in this category. '+ref(21)),
 C('Test differentiation by asking a prospect to perform the same review in their current tool and in Powder Ranger, on the same frozen job with time and outcomes recorded.'))

page('Who buys — and who should wait',
 'Start with data access, recurring pain and an accountable reviewer.',
 T(['Segment','Initial fit','Reason / condition'],[
 ['Industrial service bureaus','High, if images are accessible','Many builds and limited review time. Need an AM manager, process engineer and permission to inspect customer data.'],
 ['Process-development teams','High','Useful for changes and parameter experiments; distinguish intended experimental differences from unexpected indications.'],
 ['R&D / university labs','Useful design partners','Fast feedback and known data; willingness to pay may be lower than industrial buyers. Do not use only academic validation.'],
 ['Aerospace / medical production QA','Later, selectively','Strong evidence needs and slower acceptance. Use only inside the customer’s qualified process; no automatic release decision.'],
 ['Fleet-wide enterprise programs','Later','Expect identity, APIs, governance, integration and service commitments beyond the current prototype.']],[.27,.18,.55]),
 H('Buying group and questions to resolve'),
 P('<b>Engineer champion:</b> does the crop and persistence workflow reduce work? <b>AM manager / budget owner:</b> is the annual time value greater than the full cost? <b>Quality lead:</b> what can be concluded, what remains unreviewed and how are decisions traced? <b>IT/security:</b> where are files, who can access them and how are updates controlled? <b>Procurement/legal:</b> does the licence, support and data agreement match policy?'),
 B('Qualify raw image access, file naming, cameras, phases, layer spacing, bit depth, compression, job size and export ownership before quoting.',
   'Ask for baseline jobs/year, review hours/job, labour cost, recurring false alarms, missed observations and reporting obligations.',
   'Disqualify projects needing real-time machine control, guaranteed internal-defect detection, inaccessible proprietary streams or unsupported multi-user access.'),
 C('A team with little review volume may not justify an annual licence. Offer a bounded service only if delivery margin remains positive; do not force a subscription on a weak use case.'))

page('Compare the commercial models',
 'The best initial choice balances data locality, learning, cash and support.',
 T(['Model','Advantages','Costs / decision'],[
 ['Assisted pilot + annual local licence','Upfront learning and services revenue; recurring funding for maintenance; imagery stays local.','Recommended starting model. Requires onboarding discipline, clear entitlements, offline activation design and renewal value.'],
 ['Perpetual licence + maintenance','Familiar procurement pattern and long offline use.','Lumpy revenue; old releases accumulate. Test only with buyers rejecting subscriptions; price future maintenance and supported versions separately.'],
 ['Hosted SaaS','Central updates, collaboration and usage metering.','Terabyte upload, data permissions, storage/egress and security costs. Premature without a cloud-specific use case and acceptance evidence.'],
 ['Open core + paid support/features','Possible trust, research adoption and community adapters.','Commercial conversion and governance are unproven. Choose a deliberate licence after IP review; do not open the entire product just to acquire users.'],
 ['Services-only analysis','Fastest way to learn customer problems; no licence infrastructure initially.','Capacity limited, hard to scale and requires image transfer or customer-controlled access. Suitable bridge for a few pilots.'],
 ['OEM / reseller licensing','Access to installed customers and integrations.','Slow negotiations, dependency, margin sharing and roadmap demands. Pursue after direct customer evidence; avoid early exclusivity.']],[.25,.35,.40]),
 H('How to make the final choice'),
 P('Score models after ten interviews on willingness to pay (30%), customer deployment fit (25%), repeatable margin (20%), support load (15%) and strategic control (10%). These weights are founder judgement, not research statistics. Record rejection reasons rather than simply counting stated preferences.'),
 P('For now, use contracts to define pilot scope and annual rights. A commercial licence manager has not been implemented. Keep existing reports readable after a pilot expires; do not make customer evidence dependent on a live subscription.'),
 C('Revisit the model after three completed paid pilots and the first renewal discussions. A SaaS launch or a public open-source release would be a separate, deliberate decision.'))

page('The offer and pricing experiment',
 'One clear pilot. One simple subscription hypothesis. Explicit scope.',
 T(['Offer','Proposed price, ex VAT','Included / boundaries'],[
 ['Six-week design-partner pilot','€3,000','Up to two agreed jobs and one existing export format; one workstation; calibration/import assessment; two review sessions; findings and ROI summary. Budget 24 delivery hours.'],
 ['Annual local licence','€6,000/year','One workstation at one site; updates during term; agreed supported formats; six hours/year of included assistance as a modelling allowance. Proposed entitlement, not current activation functionality.'],
 ['Pilot conversion','€750 credit','Applied once to the first annual licence when agreed in the signed offer. First subscription cash: €5,250.'],
 ['Production onboarding','€1,500 once','Deployment, training and a documented production workflow, budget ten hours. Distinct from pilot feasibility testing; waive or reduce if already completed.'],
 ['Additional integration','Scoped quotation','New export adapters, network deployment or custom reports. Estimate effort and obtain a change order before work. No unlimited custom development.']],[.25,.22,.53]),
 P('A converting customer pays €9,750 in the first relationship year: €3,000 pilot + €5,250 discounted licence + €1,500 production onboarding. Subsequent annual licence price is €6,000 before separately agreed services. The financial model uses these exact assumptions; it is not observed demand or an announced public tariff.'),
 H('Validate willingness to pay'),
 B('Present the same scope at several price points across qualified conversations; record budget owner, alternatives and the decision to buy or decline.',
   'Ask for a paid commitment after data feasibility, not a non-binding “would you pay?” answer.',
   'Allow a data-incompatibility exit before analysis begins; define refund or service-credit terms in the pilot agreement.',
   'Limit discounts by time and scope. Exchange design-partner pricing for structured feedback, never for mandatory positive testimonials.'),
 C('Do not publish tiers, promise unlimited jobs or sell multi-seat rights until measured performance and the entitlement design support them.'))

page('The customer ROI test',
 'Use time saved in review. Treat scrap savings as an unproven upside.',
 P('Illustrative workflow: 80 jobs/year, four hours of manual review per job, 45 minutes with assisted review, and €65/hour loaded engineering cost. Both methods must include the time to open, inspect, decide, report and revisit uncertain images. Unattended analysis time is recorded separately and is not automatically labour saving.'),
 T(['Metric','Calculation','Illustrative result'],[
 ['Annual time value','80 × (4 − 0.75) h × €65/h','€16,900'],
 ['First relationship-year cost','Pilot + discounted annual licence + onboarding','€9,750'],
 ['First-year net time value','€16,900 − €9,750','€7,150'],
 ['First-year ROI','€7,150 / €9,750','73%'],
 ['Renewal-year net time value','€16,900 − €6,000','€10,900'],
 ['Break-even volume','Cost / €211.25 saving per job, rounded up','47 jobs first year; 29 at renewal']],[.31,.43,.26]),
 H('Sensitivity matters more than the headline'),
 P('At only 36 jobs/year and 1.25 hours saved per job, annual time value is €2,925. A €6,000 licence is not justified by this time-saving case. At 80 jobs, a saving of just one hour gives €5,200 and also fails the renewal test. Higher image volume alone does not create value if review is already efficient or required to remain fully manual.'),
 P('Measure counterfactuals fairly: use comparable jobs, alternate the order of tools, include setup and false-positive handling, and have an independent reviewer check missed visible events. Keep changes in staffing, part complexity and required quality scope in the record.'),
 B('Customer KPI: hours saved/job at the agreed review coverage and visible-event sensitivity.',
   'Commercial KPI: measured annual value / full annual relationship cost, with a customer-selected minimum return.',
   'Adoption KPI: use on the next real job without the founder operating the tool.'),
 C('Do not enter avoided scrap, reduced CT cost or improved material quality into the base ROI model until independently supported for that customer’s process.'))

page('A six-week pilot that produces evidence',
 'Separate feasibility, calibration, evaluation and the buying decision.',
 T(['When','Work and owner','Output / gate'],[
 ['Before signing','Founder + customer: export rights, use case, sample inspection, security constraints and workstation.','Supported-data checklist, priced scope, named reviewer and budget owner.'],
 ['Week 1','Engineering: import a frozen copy, verify camera/phase/layer mapping and intensity scale; benchmark a bounded subset.','Source manifest, coverage report, timing baseline and explicit unsupported cases.'],
 ['Week 2','Process engineer + reviewer: calibrate only inside each job; agree settings and persistence definitions.','Locked evaluation protocol. Research labels, if available, remain separate from input pixels.'],
 ['Weeks 3–4','Customer reviewers: compare manual and assisted review on held-out jobs; audit unflagged examples.','Paired timings, known visible events found/missed, false-alarm workload and review decisions.'],
 ['Week 5','Engineering: investigate discrepancies, deployment reliability and support time.','Issue list and fixes; changes that alter detection require new held-out evaluation.'],
 ['Week 6','Budget owner + QA + founder: review results and annual value.','Convert, extend under a new bounded scope, or stop with customer-owned reports and an explanation.']],[.18,.46,.36]),
 P('The two-job commercial scope is a feasibility package, not a statistically representative validation study. If one job informs threshold tuning, the other is the minimum held-out check; it is still insufficient to claim performance across machines, materials or part families. Add a separate evaluation programme before broad industrial claims.'),
 P('Suggested pilot targets, to negotiate rather than advertise as achieved: at least 30% median review-time reduction; at least 90% recall of the independently enumerated visible events within the sampled scope; and a review workload the customer can sustain. Sample size, event definition and acceptable uncertainty must be written down.'),
 C('Stop or narrow the pilot if mapping is ambiguous, source integrity cannot be preserved, or the persistence definition changes the interpretation. Never hide unreadable frames or warm-up layers from the evaluation denominator.'))

page('Validate the observation, not just the algorithm',
 'A synthetic regression test is necessary engineering evidence, not process validation.',
 P('Define an event as a visible spatial/temporal phenomenon with a documented start, end, stage, camera and matching rule. Report both occurrence-level and track-level performance; otherwise repeated flags on the same region can inflate apparent detection counts. The named-layer and Aalto persistence representations must be reconciled before a common benchmark is claimed.'),
 T(['Measure','Method / interpretation'],[
 ['Visible-event recall','Matched reviewer events / all reviewer events in the evaluated scope. Report denominator and confidence interval; stratify by job, phase and phenomenon.'],
 ['Precision / workload','Accepted useful flags / all reviewed flags; also regions to inspect per 1,000 comparable layers and minutes per job.'],
 ['Misses','Inspect a random sample of unflagged layers and known difficult cases. Reviewers must not see the algorithm’s flags during ground-truth enumeration.'],
 ['Agreement','Two reviewers independently label a subset, reconcile differences and retain both original opinions. Distinguish uncertain observations from negatives.'],
 ['Robustness','Missing/corrupt images, saturation, exposure drift, camera movement, changing geometry, different resolutions, long jobs and interrupted/resumed runs.'],
 ['Performance','Runtime, peak RAM, disk/cache growth, I/O, source location and hardware specification. Repeat across cold and warm caches.']],[.26,.74]),
 P('Split calibration and evaluation by complete jobs, then by machine/material where possible; neighbouring frames are correlated and cannot provide an honest random-image hold-out. Researcher Aalto annotations can help calibration or external scoring with documented permissions and splitting; they are never overlaid on analysis inputs. No satisfactory reference job is currently available.'),
 P('For a later material-quality claim, correlate registered in-situ indications with independent NDE, sectioning or testing under an appropriate protocol. NIST emphasizes calibration, measurement limits and registration metadata in this area. '+ref(8)+'; '+ref(9)+'; '+ref(10)),
 C('Publish coverage: measured, evaluated, warm-up, missing, failed and excluded frames. A blank map must not be interpreted as proof of an anomaly-free build.'))

page('Assisted distribution: a practical operating system',
 'Use AI assistance to prepare high-quality work; keep relationships and approvals human.',
 T(['Activity','Assistant prepares','Founder / specialist owns'],[
 ['Account research','Public company profiles, LPBF evidence, likely workflow, source-linked hypotheses and a short account brief.','Validate fit, identify a legitimate contact route, approve outreach and comply with local rules.'],
 ['Discovery','Question list, agenda, consent-aware notes, action summary and CRM draft.','Conduct the interview, verify facts and secure agreement for any recording or data access.'],
 ['Demo / proposal','Tailored script, ROI calculation, scope, compatibility checklist and draft quote.','Check claims and cost, approve price, contract and transmission.'],
 ['Onboarding','Import mapping draft, test checklist, issue triage and documentation.','Authorize access and deployment, validate technical mapping, sign off delivery.'],
 ['Customer success','Usage/review summaries from consented data, renewal agenda and support knowledge articles.','Review interpretation, protect confidential data and handle commercial commitments.'],
 ['Marketing','English copy, captioned videos, technical articles and case-study drafts.','Approve evidence, brand rights, customer permission and publication.']],[.23,.40,.37]),
 P('A lightweight CRM can begin as a controlled table: account, region, contact provenance, segment, machine/export, jobs/year, review time, decision owner, data restrictions, stage, next action/date, pilot value and actual delivery hours. Store contact records separately from customer process imagery. Define retention and access rules.'),
 H('Weekly cadence'),
 B('Monday: review ten researched accounts and select a small, relevant outreach batch.',
   'Tuesday–Wednesday: discovery and short demonstrations; capture objections verbatim and update assumptions.',
   'Thursday: pilot delivery and customer evidence review; convert recurring support questions into documentation.',
   'Friday: pipeline, hours, cash, defects and next-week decisions. Remove stalled opportunities with no owner or usable data.'),
 C('This report does not send messages, publish a site, upload customer images or start campaigns. External outreach and publication require the founder’s explicit authorization.'))

page('Founder-led sales and a measurable funnel',
 'A small qualified pipeline is more useful than a large download count.',
 P('An illustrative first-year funnel is 120 qualified accounts → 40 discovery meetings → 24 technically usable sample datasets → 16 paid pilots → 8 annual customers. These are planning targets, not industry conversion benchmarks. Track each transition and replace assumptions with observed rates after the first ten conversations.'),
 T(['Stage','Exit condition','Next action'],[
 ['Qualified account','LPBF use, raw-image access and recurring review burden are plausible.','Ask for a 20-minute workflow discussion through a legitimate contact route.'],
 ['Discovery complete','Named champion, reviewer, buyer, timing and baseline workload.','Inspect a small permitted data sample; do not ask for terabytes initially.'],
 ['Technically feasible','Known format, camera/phase mapping and supported analysis scope.','Present a bounded paid pilot and a specific success decision.'],
 ['Paid pilot','Signed scope, access and data responsibilities, kickoff and evaluation dates.','Run the six-week protocol; log delivery time and risks.'],
 ['Annual proposal','Customer confirms measured value and a deployment owner.','Agree entitlement, support, renewal and evidence-retention terms.'],
 ['Renewal','Recurring usage and value measured before term ends.','Review 60–90 days before expiry; resolve non-use before proposing more seats.']],[.25,.43,.32]),
 H('Channels to test in order'),
 P('Start with warm technical introductions and narrowly relevant professional outreach, then a public-data webinar with a reproducible walkthrough, then consented pilot case studies. Test partner referrals once onboarding is repeatable. Paid ads, broad cold-email automation and an expensive booth should wait until the ICP and conversion story are clear.'),
 P('Professional outreach still has legal requirements. U.S. CAN-SPAM covers commercial email, including B2B, and the French CNIL describes conditions for professional prospecting and opt-out. Verify each target jurisdiction and use accurate identity and an easy objection mechanism. '+ref(15)+'; '+ref(16)),
 C('Primary commercial dashboard: qualified meetings, feasible datasets, paid pilots, conversion, delivery hours, gross contribution and renewal usage. Downloads and video views are secondary signals.'))

page('Marketing that the evidence can support',
 'Lead with the workflow; make the call to action a pilot conversation.',
 P('The delivered 27-second English film combines a labelled illustrative LPBF introduction with actual NIST crops and Powder Ranger renders, a priority score, a cyan photographic stack and a report preview. It uses an original synthesized soundtrack and English captions. It is a data-driven presentation, not a screen recording or a performance-validation study.'),
 T(['Asset','Purpose / suggested message'],[
 ['27-second presentation','“Thousands of layers. One clearer view.” Show context → priority → 3D → evidence. Finish with “Bring a build. See what changed.”'],
 ['Focused landing page','Who it helps, supported workflow, actual screenshots/renders, data-locality explanation, limitations and “Discuss a pilot”. Do not label planned features as released.'],
 ['One-page product sheet','Supported image types/metadata, deployment model, review/report behavior and the six-week pilot scope. Include version and contact owner.'],
 ['Technical walkthrough','Use a public job, show raw images, calibration, false positives, persistence settings and retained report. Publish enough settings to reproduce the example.'],
 ['Case study','With written customer permission: problem, baseline, scope, measured outcome, workload, limitations and customer quote checked for accuracy.']],[.29,.71]),
 H('A four-week content experiment'),
 B('Week 1: introduce the review problem and share the short film with a pilot invitation.',
   'Week 2: explain matching crops and why global exposure shifts can create misleading flags.',
   'Week 3: explain persistence and review scores, including a transient single-layer example and the quality-interpretation limit.',
   'Week 4: host a short public-data walkthrough and invite qualified teams to discuss their export format.'),
 P('Use public-data attribution and avoid a suggestion of NIST endorsement. Recheck provider/media terms and trademark clearance before paid advertising. The underlying example comes from the documented NIST data record. '+ref(18)+'; '+ref(19)),
 C('Never advertise “detects all defects”, “certifies the build”, “validated severity”, “any machine” or “terabyte-ready” without matching evidence and supported scope.'))

page('Global launch, controlled delivery',
 'A global target market does not require simultaneous local operations everywhere.',
 P('Wave 1: remotely supported English-language pilots with technically compatible teams in Europe and North America. This is a delivery-capacity choice, not a claim that demand elsewhere is lower. Wave 2: selected APAC partners or design partners when time-zone coverage, import feasibility and contracting are understood. Local deployment is helpful for data control but does not remove procurement or legal requirements.'),
 T(['Route','What to prove before investment'],[
 ['Direct customers','Repeatable import, measurable time value, manageable assistance and a named internal owner.'],
 ['AM consultants / labs','Referral fit, customer consent, technical independence and clear ownership of support. Pilot a non-exclusive referral agreement first.'],
 ['Machine resellers / OEMs','Data-access rights, supported versions, compatibility tests and non-conflicting support responsibilities. Negotiate on proven demand; avoid early exclusivity.'],
 ['Research community','Reproducible examples and appropriately licensed datasets; academic feedback is useful but not proof of industrial demand.'],
 ['Events','Prebook relevant conversations and a small number of demos; measure qualified follow-ups rather than foot traffic.']],[.30,.70]),
 P('Formnext is scheduled for 17–20 November 2026 in Frankfurt according to the official visitor page. A first visit with pre-arranged meetings is a more proportionate experiment than committing to a booth. No event attendance or booking has been arranged. '+ref(17)),
 H('Partner economics and control'),
 P('A referral-fee hypothesis of 10–15% of collected first-year licence revenue can be tested only after direct margins are known. State whether services are excluded, when commission is earned and how customer data is handled. Reseller discounts, technical support and territory commitments require a separate model; do not assume they fit the direct-sales forecast.'),
 C('Global practical checklist: contracting entity, invoice currency and taxes, payment collection, applicable export/end-use restrictions, insurance, local support hours and permission to access process data. Obtain country-specific advice when a concrete sale is in scope.'))

page('Product roadmap ranked by customer value',
 'Make evidence trustworthy and jobs manageable before broadening the feature list.',
 T(['Priority','Feature / improvement','Acceptance evidence'],[
 ['Now: integrity','Shared occurrence and persistence semantics; source manifests for both adapters; explicit legacy-run status.','Moving/gapped/branched tracks, resume equivalence and reviewed-run migrations pass.'],
 ['Now: deployment','Clean Windows acceptance, native dialogs, versioned backup/restore, signed build and dependency/security process.','A customer IT reviewer can install, update and recover a supported build without losing decisions.'],
 ['Next: workload','Metadata paging, disk-aware caches, job resumability, coarse-to-fine region analysis and estimate based on a sample.','Full-job runtime, peak RAM and disk use measured on the agreed standard PC.'],
 ['Next: interpretation','Per-region gray/texture timeline, global illumination diagnostics, drift/registration checks and coverage map.','Reviewer can explain a flag, identify unmeasured regions and distinguish optical drift from a local event.'],
 ['Then: comparison','Separate reference-job mode, approved reference selection, stage/coordinate registration and reference versioning.','Known placement/layer differences handled explicitly; no cross-job threshold leakage into single-job mode.'],
 ['Later: integration','CAD/physical calibration, part IDs, export API, collaborative review and site deployment.','Driven by signed pilot needs and validated coordinate transforms, permissions and storage costs.']],[.18,.44,.38]),
 P('Estimate the first hardening tranche at 4–8 engineer-weeks as a planning range, subject to implementation and migration design. Import adapters can dominate cost; quote them after a sample audit. Preserve a small dependency footprint on the runtime path and avoid adding GPU requirements just for presentation.'),
 H('Potential specialist detectors'),
 P('After the common measurement and validation framework is stable, evaluate directional streak features, recoater-stripe continuity, local texture and saturation diagnostics. Compare each addition against the current temporal baseline and reviewer workload. Add a technique only if held-out evidence improves a defined use case; a more complex model is not automatically more useful.'),
 C('The reference comparison is a later product mode. Its reference calibration, registration and evaluation must remain separate from an independent single-job analysis.'))

page('Architecture: unify the domain, preserve results',
 'The audit reduced coupling; the next refactor should unify meaning.',
 P('The runtime now separates the HTTP adapter and image-preview cache from the main Application coordinator. Report-volume rendering no longer imports the HTTP application to obtain a preview. Settings/catalog/calibration JSON writes share atomic persistence, and review/report paths share source-identity guards. These are bounded changes with regression coverage, rather than a wholesale rewrite.'),
 T(['Layer','Proposed responsibility'],[
 ['Import adapters','Convert each supported export into Job → Channel(camera, stage) → Frame(position, source identity, geometry). Preserve unknown metadata explicitly.'],
 ['Measurements','Immutable, versioned image-derived values, intensity scale and ROI. Cache measurements independently of detector thresholds.'],
 ['Detection / tracking','A shared Occurrence and Track model for both named-layer and acquisition datasets; explicit continuity, split and merge rules.'],
 ['Review','Decision keyed to run and indication identity; comment, revision and history. Filtered views must not delete underlying observations.'],
 ['Visualization / reports','Consume a stable snapshot and coordinate mapping; render the same priority, persistence and scope in 2D, 3D and exports.'],
 ['Persistence / transport','Repository interface over SQLite/files; bounded queries, transactional migrations and thin HTTP handlers.']],[.27,.73]),
 H('Migration sequence'),
 B('Document existing schema and detector versions. Add shared domain types without replacing the stores.',
   'Introduce occurrence records and a deterministic tracking service with cross-adapter contract tests.',
   'Store run/source manifests; mark legacy runs as legacy, and preserve their decisions and exports.',
   'Create an explicit re-analysis/migration action with backup, comparison and rollback. Change engine versions when detection meaning changes.',
   'Replace full-list API responses with pagination/streamed summaries; profile before selecting new storage technology.'),
 C('The highest-risk inconsistency is persistence association: a moving indication can split prematurely when matched against its historical peak box. The source audit includes a three-frame reproduction. Resolve this before claiming equivalent track behavior across every job format.'))

page('Security, deployment and support',
 'A local application still needs a maintained release process.',
 P('The current Windows package bundles Python, NumPy, Pillow and the local web UI. The server uses loopback, with Host/Origin checks and bounded JSON input. This is not an authenticated network service; do not expose its port to a company LAN or the internet. Local execution does not establish that every endpoint, dependency or file format is secure.'),
 T(['Before broader distribution','Owner / deliverable'],[
 ['Reproducible release','Engineering: pinned dependency inventory, licence notices, hashes, build log, version manifest and clean-machine acceptance. Add an SBOM and vulnerability review.'],
 ['Trusted updates','Engineering + security: sign executables and update metadata; document supported versions, update verification and rollback. Code-signing credentials are not part of this prototype.'],
 ['Data resilience','Engineering + customer IT: backup/restore of settings, manifests, measurements and decisions; retain source paths and verify changed/missing files. Test disk-full and interrupted exports.'],
 ['Desktop experience','QA: native folder dialogs, launch/open browser, port conflicts, repeated launches, installation, update and removal on supported Windows versions.'],
 ['Customer support','Founder: defined response hours and channels, issue severity, diagnostic bundle with redaction, version identification and escalation path. No unsupported 24/7 SLA.'],
 ['Incident handling','Named security owner: intake route, triage, affected versions, remediation, notification decision and documented support period.']],[.30,.70]),
 P('For initial pilots, propose a two-business-day noncritical response target during agreed support hours, not a guaranteed resolution time. Escalate data-integrity problems immediately and pause affected interpretation. Review this service promise against staffing and contractual liability before selling it.'),
 P('As of this report date, EU CRA reporting obligations begin on <b>11 September 2026</b>; relevant notifications have 24-hour and 72-hour stages. Full application is scheduled for <b>11 December 2027</b>. Have counsel assess scope for the intended distribution and connected use; “offline” or “open source” is not a blanket exemption. '+ref(11)+'; '+ref(12)),
 C('A headless executable self-test is valuable but does not replace an IT acceptance test, signing, dependency review or a security assessment.'))

page('Legal, intellectual property and quality boundaries',
 'Resolve rights and claims before turning a prototype into a commercial promise.',
 H('Name, code and dependencies'),
 P('Clear the Powder Ranger name and badge before significant marketing spend. The playful allusion may require assessment of similar marks, relevant goods/services and target countries; no availability or infringement conclusion is made here. Review candidate software/service classes with a trademark professional and keep an alternative name ready. The USPTO explains comprehensive clearance and likelihood of confusion. '+ref(13)+'; '+ref(14)),
 P('Confirm ownership of project code, contractor contributions and pre-existing employer/research obligations. Review licences for shipped dependencies and binary components, retaining notices and redistribution conditions. A source-code release needs an explicit licence choice; absence of a licence is not an open-source strategy. Keep the video encoder and marketing tools outside the shipped runtime.'),
 H('Customer contracts and data'),
 B('Use a pilot statement of work, software terms, support policy and confidentiality/data-access agreement reviewed for the actual jurisdiction.',
   'Define customer ownership of raw images and review results; specify licence rights, retention, return/deletion and what diagnostic access is permitted.',
   'Require separate opt-in for research reuse, model training, public case studies or image publication. Do not bundle that consent into ordinary support.',
   'Agree limitation of purpose, acceptance criteria, change control, fees, payment, warranty/liability allocation and appropriate insurance with qualified advisers.'),
 H('Quality and regulatory interpretation'),
 P('ISO/ASTM 52920 addresses qualification principles for industrial AM processes and production sites; its public overview does not establish that Powder Ranger is certified or compliant. Software observations can support an evidence workflow only within the customer’s qualified process. Obtain the applicable full requirements before making a compliance mapping. '+ref(22)),
 P('Review CRA scope, relevant privacy rules and cross-border sales obligations before a concrete commercial distribution. The report identifies practical actions, not a legal opinion or a full compliance assessment. Public-data licence and attribution conditions are separate from software licensing. '+ref(12)+'; '+ref(19)),
 C('Do not promise material accept/reject decisions, automatic NDE replacement or regulatory qualification from powder-bed photographs alone.'))

page('Financial model: assumptions you can change',
 'All figures are illustrative EUR, excluding VAT. They are not market forecasts.',
 T(['Assumption','Base input','Treatment'],[
 ['Pilot fee / labour','€3,000 / 24 h','€65/hour externally purchased delivery cost plus €100 tools: €1,660 direct cost/pilot.'],
 ['Annual licence','€6,000 list','€750 one-time conversion credit: €5,250 first subscription cash. €6,000 on renewal.'],
 ['Onboarding','€1,500 / 10 h','€650 direct delivery cost. Waivers reduce revenue and must be modelled explicitly.'],
 ['Annual support','6 h/account','€390 per active end-of-year account; full-year charge is a conservative support-cost assumption.'],
 ['Collection / administration','2% of cash bookings','Planning allowance, not a verified payment-provider fee.'],
 ['Fixed operating cost','€90k Y1; €120k base Y2','Founder development/sales and overhead. Delivery labour above is separately purchased and is not also included in fixed compensation.'],
 ['Timing','Midyear activation','Annual cash upfront; licence revenue recognized half in activation/renewal year and half in the next. Services delivered/recognized in the same year.']],[.27,.25,.48]),
 P('Cash bookings include collected pilot, onboarding and annual licence amounts. Recognized revenue spreads the licence service over its term. End-year ARR is the number of active subscriptions multiplied by the €6,000 renewal list price; it is a nominal renewal run-rate and excludes services, not recognized revenue or a cash balance.'),
 P('The simplified model excludes VAT, income/corporate taxes, financing, receivables delays, capital equipment and accounting-specific revenue/cost policies. It assumes every pilot and onboarding project shown is delivered and paid in-year. An accountant should adapt it before funding decisions. No grant, subsidy, investor commitment or purchase order is assumed.'),
 P('Year-1 fixed-cost envelope: €60k founder development/sales capacity, €10k legal/security/release support, €8k customer development/travel, €6k tools/insurance/admin and €6k contingency. These are allocation hypotheses within €90k; delivery contractors are in variable cost. Revise with actual local quotes.'),
 C('Editable inputs and exact calculations are supplied in financial_model.json and research/business_model.py. If the founder performs delivery, adjust cash costs while still recording that time; never count the same labour twice.'))

page('Two-year scenarios: revenue is not cash',
 'A useful business can still lose money while it is being established.',
 T(['Scenario / year','Pilots / new / renew','End customers','Nominal ARR'],[
 [name+' Y'+str(y+1),f"{r['pilots']} / {r['new']} / {r['renewals']}",str(r['end_customers']),f"€{r['list_price_arr']:,.0f}"]
 for name,years in M['scenarios'].items() for y,r in enumerate(years)],[.26,.30,.20,.24]),
 T(['Scenario / year','Cash bookings','Recognized revenue','Operating result','Cash surplus'],[
 [name+' Y'+str(y+1),f"€{r['cash_bookings']:,.0f}",f"€{r['recognized_revenue']:,.0f}",f"€{r['operating_result']:,.0f}",f"€{r['cash_surplus']:,.0f}"]
 for name,years in M['scenarios'].items() for y,r in enumerate(years)],[.23,.19,.20,.19,.19]),
 P('Base case: 16 paid pilots and 8 annual conversions in year 1; 28 pilots, 14 new annual customers and 7 renewals in year 2. The 7 renewals out of 8 prior customers represent 87.5% customer retention by assumption. Year-2 end-customer count is 21, not 22; the one nonrenewal is excluded.'),
 P('The base case produces a €24,920 first-year cash deficit and a €32,320 second-year cash surplus, yet year-2 recognized operating result is still negative at €4,430. Upfront collections explain the difference. Downside cumulative two-year cash deficit is €148,020. Upside requires 1,776 delivery hours in year 2 and a €160k fixed-cost envelope; it cannot be delivered by marketing optimism alone.'),
 C('Do not derive required starting capital from annual net cash alone. Build a monthly collection/payroll model, include late payments and minimum reserve, and test at least 9 months of operating runway before hiring or committing to long fixed costs.'))

page('Unit economics and delivery capacity',
 'Support hours and onboarding effort are the critical constraints.',
 T(['Unit','Revenue / cost assumption','Contribution before sales & fixed cost'],[
 ['Pilot','€3,000 − €1,660 delivery/tools − €60 collection','€1,280 / 42.7%'],
 ['First annual + onboarding','€6,750 − €650 onboarding − €390 support − €135 collection','€5,575 / 82.6%'],
 ['Full converting relationship','€9,750 − €1,660 − €650 − €390 − €195 collection','€6,855 / 70.3%'],
 ['Renewal licence','€6,000 − €390 support − €120 collection','€5,490 / 91.5%']],[.27,.48,.25]),
 P('These are modelled contribution margins, not audited software gross margins. Acquisition cost, development, founder sales, legal, security and overhead remain to be paid. There is no reliable lifetime-value estimate until retention and support behaviour are observed.'),
 H('Capacity check'),
 P('Base year 1 requires 512 purchased delivery hours. Base year 2 requires 938: 672 for pilots, 140 for onboarding and 126 for support. These are separate from founder development and sales. Upside year 2 requires 1,776 hours before coordination, travel or support peaks; plan dedicated delivery capacity and do not book overlapping pilots without an owner.'),
 H('Stress the support assumption'),
 P('If average support rises from 6 to 30 hours per active customer in base year 2, direct cost increases by €32,760 (21 × 24 × €65). The €32,320 cash surplus becomes a €440 deficit. This is why import quality, documentation and bounded support are central to the business model.'),
 P('Test fully loaded acquisition cost at €1,500–€3,500 as an initial sensitivity range, then replace it with measured founder time, events, travel and marketing spend per paying customer. This is not an external CAC benchmark. Retain customers through recurring evidence value; do not rely on report lock-in.'),
 C('Control points: hours per pilot; unsupported-format rate; onboarding hours; quarterly support per account; renewal intention; and contribution after actual acquisition costs. Raise prices, narrow scope or stop a segment if the economics do not work.'))

page('Risk register and response',
 'Rank risks by decision impact; assign an owner and an observable trigger.',
 T(['Risk / priority','Trigger and mitigation','Owner'],[
 ['Incorrect interpretation / high','Missed visible event or score read as material severity. Publish scope, inspect unflagged samples, retain human decisions and stop affected claims.','Technical + QA'],
 ['Persistence / provenance / high','Different tracks across formats, changed source or legacy identity gap. Versioned common schema, source manifests and explicit re-analysis.','Engineering'],
 ['Weak willingness to pay / high','Prospects praise the demo but decline paid scope. Test budget-owner commitments; reduce target segment or switch to scoped services.','Founder'],
 ['Support overload / high','Pilot >24 hours or annual support trajectory >6 hours without extra revenue. Improve adapters/docs; change scope and quote work before delivery.','Delivery lead'],
 ['Data inaccessible / high','OEM export restrictions, encrypted format or customer ownership limits. Require sample and rights checklist before a paid analysis commitment.','Founder + legal'],
 ['Security / legal launch gap / high','Unpatched dependency, unowned incident process or unresolved CRA scope. Independent review, supported release lifecycle and distribution gate.','Security + legal'],
 ['Scale failure / high','RAM/disk/runtime outside customer limits. Benchmark, page results and narrow supported size; do not sell unmeasured capacity.','Engineering'],
 ['Brand / IP / medium','Similar mark or code ownership conflict. Clearance, ownership inventory and alternative name before promotion.','Founder + counsel'],
 ['Sales concentration / medium','One partner or customer controls roadmap/revenue. Non-exclusive agreements and several independent design partners.','Founder'],
 ['Cash / capacity / high','Delayed pilots, slow payments or concentrated support demand. Monthly forecast, reserve and milestone-based spend.','Founder + accountant']],[.29,.55,.16]),
 P('Review the register weekly during pilots and monthly thereafter. For each high risk, record status, last evidence, next action, owner and due date. “Accepted” needs a bounded pilot scope and a decision-maker; it does not mean the issue is fixed.'),
 C('No scale-up if customers cannot reliably interpret the evidence, if source identity is uncertain, or if each deployment depends on unpriced custom work.'))

page('Your next 90 days',
 'A sequence of decisions, deliverables and stop/go gates.',
 T(['Period','Actions','Evidence required'],[
 ['Days 1–7','Review the audit; assign owners for persistence and source manifests; freeze pilot copies; commission brand/CRA scope review; identify ten discovery candidates.','Written pilot boundary, issue backlog, release owner and outreach drafts ready for approval.'],
 ['Days 8–30','Complete interviews; fix shared tracking/provenance; run clean-machine acceptance; prepare one-page offer, compatibility form and monthly cash plan.','Two or three qualified design partners, measured manual baseline, signed scope and a deployable supported build.'],
 ['Days 31–60','Start 2–3 bounded paid pilots, staggered to protect delivery capacity; test held-out jobs and track false-positive workload and hours.','Customer-reviewed results, data integrity, repeatable imports and no hidden manual intervention.'],
 ['Days 61–90','Finish pilots, offer annual conversion where value is proven; refine price/scope; publish only consented evidence; decide one next adapter.','At least one real buying decision, actual unit costs and a written decision to expand, extend narrowly or stop.']],[.19,.46,.35]),
 H('Suggested day-90 go/no-go criteria'),
 B('At least two completed paid pilots with technically usable jobs and a reviewer-owned outcome.',
   'A customer confirms meaningful time saving at an acceptable missed-visible-event review scope; no unqualified material-quality claim.',
   'One or more annual conversions, or a documented procurement path with a real budget owner; not just free-trial enthusiasm.',
   'Median pilot delivery near the 24-hour budget and a credible path to the support allowance.',
   'High-priority integrity issues closed or the commercial scope explicitly narrowed, with a maintained security/release process.'),
 P('Calendar mapping from 9 September 2026: first-month decisions by early October; pilot evidence during October–November; day-90 review in early December. Formnext can support pre-arranged conversations during the pilot period, but the technical and commercial gates take precedence over an event deadline.'),
 C('If these gates fail, choose one response: narrow the ICP/data formats, sell a profitable bounded service, or pause commercial expansion while resolving the technical evidence gap. Avoid adding features to evade a buying decision.'))

page('Ready-to-use discovery and outreach',
 'Drafts for human review. Nothing has been sent.',
 H('Discovery script: 20 minutes'),
 B('Which decision do layer images support today, and who is accountable for it?',
   'Walk through the most recent build review: job size, time, tool, flags, final report and unresolved questions.',
   'Can you export original images with camera, layer, phase, timing and exposure information? Who authorizes access?',
   'Which visible events matter, and how do you determine whether an indication is relevant?',
   'How many jobs are reviewed annually? Which work would actually be reduced if triage improved?',
   'What can remain local, and what software/security/procurement requirements apply?',
   'Who would review a pilot, approve the budget and decide on an annual licence?',
   'What result would make a paid pilot useful, and what would make you stop?'),
 H('Example introduction — personalize before sending'),
 P('<b>Subject:</b> Reviewing LPBF layer images at [Company]<br/><br/>Hello [Name],<br/>I am developing Powder Ranger, a locally deployed tool that helps engineers review changes in powder-bed photographs using matching before/after crops, persistence and a traceable report.<br/><br/>I would like to understand how your team reviews exported layer images and where time is lost. The software flags visual indications for human review; it does not certify material quality.<br/><br/>Would a short workflow discussion be relevant? If so, I can share a public-data demonstration and, if the format fits, discuss a bounded paid pilot.<br/><br/>[Real name, role, company and contact details]<br/>If this is not relevant, let me know and I will not follow up.'),
 P('Adapt identification, contact provenance, opt-out and any required address to the jurisdiction. Do not assert that the recipient uses a particular system unless a reliable source confirms it. Do not include confidential customer data in public outreach.'),
 C('After each call: distinguish observed facts, customer statements and your inference. Update the price/value hypothesis and next action; request only the smallest permitted data sample needed for feasibility.'))

page('Pilot statement of work: drafting checklist',
 'A concrete commercial scope to take to the customer and legal adviser.',
 T(['Clause','Starting content to adapt'],[
 ['Purpose','Evaluate single-job visual image triage and reporting for [named workflow]. No material acceptance, machine control or guaranteed defect detection.'],
 ['Scope','[Two jobs], [one export format], [one workstation], known cameras/phases and documented data size. Confirm exact files before signature.'],
 ['Customer inputs','Named reviewer and IT contact; permitted frozen source copies; layer/phase mapping; timed manual baseline and access authorization.'],
 ['Supplier deliverables','Import assessment, versioned analysis settings, review sessions, retained-observation reports, limitations, timing/coverage results and a closing decision meeting.'],
 ['Validation','Agreed event definition, held-out job, unflagged sampling, reviewer independence and success/stop criteria. No implied accuracy outside that scope.'],
 ['Fees and changes','€3,000 proposed fixed scope; payment schedule and incompatibility exit agreed explicitly. Extra adapter/jobs/review time require a signed change order.'],
 ['Data and IP','Customer owns inputs and review results; supplier licence rights stated separately. Retention/deletion, support access and optional research reuse documented.'],
 ['Support and expiry','Named channel and response hours, supported version, incident handling and end date. Reports remain readable; no assumed licence renewal.'],
 ['Conversion','Optional €750 first-annual-licence credit under agreed timing; annual rights and production onboarding separately described.'],
 ['Legal / acceptance','Confidentiality, liability, insurance, governing law, dispute handling and acceptance process reviewed by qualified counsel.']],[.25,.75]),
 P('Do not use this checklist as a ready-signed legal agreement. Turn it into a specific proposal after technical feasibility; remove any field or service you cannot deliver. Do not require research data reuse or a favourable testimonial as a condition of ordinary software support.'),
 C('Commercially useful evidence at close: actual delivered hours, customer baseline, assisted-review results, limitations, decision-owner feedback and a signed next-step decision.'))

page('Code audit: changes delivered',
 'Reproduced failures, bounded fixes and regression evidence.',
 T(['Area','Change and why it matters'],[
 ['Image identity / P1','Preview cache includes file size and nanosecond mtime. Named-layer review, 3D and export verify indexed metadata; report sources are checked before/after rendering.'],
 ['Library state / P1','Failed selection restores the prior job and preference snapshot. Invalid import choices no longer partially replace the active review context.'],
 ['API/config / P2','Reject non-object and non-finite JSON with bounded HTTP 400 responses. Validate malformed alias/ROI/regex/numeric configuration types.'],
 ['Persistent state / P2','Shared atomic JSON helper preserves prior files if serialization or replacement fails. Catalog memory updates only after a successful write.'],
 ['Calibration / P2','Unreadable Aalto sample images are reported and skipped; actual valid counts are used. A wholly unreadable channel fails explicitly.'],
 ['Architecture / P2','Extract HTTP handling and previews from the application coordinator; remove the report-volume dependency on the application module.'],
 ['Other fixes','Preparation/import cancellation reported coherently; Aalto report paths indexed once; remaining English crop label corrected.']],[.27,.73]),
 P('<b>Verification:</b> 74 Python tests and six JavaScript suites passed after the source changes. Regression tests cover changed files, report snapshots, malformed JSON/configuration, failed library selection and atomic storage. The original four targeted tests failed before the fixes; baseline and final logs are retained.'),
 P('Tests also cover shared priority values, retain/dismiss navigation, matching crops, stage/persistence filtering, report templates and simulated 3D behavior. The desktop build has an isolated frozen-binary acceptance check for startup, synthetic analysis, review, report generation, assets and Tcl/Tk availability. Public datasets and user decisions are not bundled.'),
 P('The full findings, source modules, reproduction commands and severity definitions are supplied separately in <b>CODE_AUDIT_0.3.1.md</b>. Application version 0.3.1 preserves detector/cache versions; existing reviewed jobs are not silently reclassified.'),
 C('These checks support engineering confidence in the changed paths. They do not establish industrial detection accuracy, complete security or multi-terabyte performance.'))

page('Open audit findings and release gates',
 'Close these in order before broad industrial claims.',
 T(['Priority','Remaining issue','Required next evidence'],[
 ['P1','Named-layer tracking matches the historical peak box; Aalto links adjacent occurrences. A moving region can split prematurely.','Shared occurrence model, explicit split/merge rules, migration and cross-adapter regression tests. Three-frame reproduction supplied.'],
 ['P1','Historic Aalto analysis lacks measurement-time source metadata; current export guards only its snapshot interval.','New source manifests and immutable identity; legacy status and explicit re-analysis. Size/mtime is not a cryptographic hash.'],
 ['P1','Some metadata and Aalto association are unbounded; terabyte readiness is unproven.','Full-job benchmark on a specified standard PC, paged API and bounded memory/disk behavior.'],
 ['P1','Commercial deployment/security lifecycle incomplete.','Clean-machine human acceptance, signing, SBOM/dependency review, backups, vulnerability process and legal scope review.'],
 ['P2','Report preparation can hold locks and buffer substantial content; native dialogs and install lifecycle need human QA.','Responsive preparation, atomic report-file publication, crash/disk-full tests and native Windows acceptance.'],
 ['P2','Cyan geometry and 0–100 score can be overinterpreted.','Visible limitations, physical-coordinate calibration where available and independently evaluated use cases.']],[.14,.43,.43]),
 P('The approved browser runtime could not initialize in this environment. Automatic review refused an independent Playwright/Edge fallback because it would bypass the required browser path. No workaround was used. JavaScript tests simulate DOM/WebGL behavior; fresh visual interaction and real native installation remain unverified in this audit.'),
 P('Decision: maintain supervised use on fixed copies of supported public/customer images, with human interpretation and explicit scope. Do not expose the loopback server as a network service, claim material quality assurance or sell unlimited-data performance. The next engineering investment should close integrity and scale gaps before introducing reference comparison or enterprise features.'),
 C('The complete request results in an improved codebase, a presentation video and a commercial plan. It does not create customers, validate production quality or authorize public distribution. The next commitment should be a tightly scoped, technically qualified pilot.'))

source_groups=[list(range(1,8)),list(range(8,15)),list(range(15,23))]
for j,ids in enumerate(source_groups):
    blocks=[]
    for n in ids:
        title,url=S[str(n)];blocks.append(P(f'<b>[{n}] {title}</b><br/><link href="{url}" color="#166a87">{url}</link>'))
    blocks.extend([H('Evidence discipline'),P('Research checked on 9 September 2026. Vendor pages establish vendor-stated features and the displayed offer, not independent performance. Prices, compatibility and event details may change. Legal/standards sources are public guidance or overviews; they do not replace assessment of the actual distribution and customer use.'),
       P('Business choices, offer prices, funnel, staffing and financial scenarios in this report are proposed assumptions. No TAM estimate is inferred from the size of the wider additive-manufacturing market. No customer interview, paid conversion or measured commercial demand is asserted. Local implementation and test claims refer to the accompanying code audit and logs.')])
    page('Sources and evidence / '+str(j+1),'Primary sources, live links and explicit limits.',*blocks)

page('Funding and the operating plan',
 'Buy evidence in small increments; preserve the ability to change direction.',
 T(['Route','When it fits','Decision rule'],[
 ['Founder-funded / customer-funded','A bounded hardening tranche and a few paid pilots.','Recommended first route if personal/business runway permits. Cap spend and avoid a full team before paid evidence.'],
 ['Services-funded product','Customers pay for useful, narrowly scoped import/review work.','Track product development separately from delivery. Stop custom work that does not recur or pay for itself.'],
 ['Research / innovation funding','A defined technical validation or interoperability programme.','Investigate actual open calls and eligibility with the appropriate local adviser. No grant amount, award or eligibility is assumed here.'],
 ['Angel / strategic investor','Pilot conversion and a credible recurring-software opportunity already exist.','Prepare evidence, ownership, security roadmap and a monthly use-of-funds plan. Review control, dilution and commercial restrictions.'],
 ['Institutional venture capital','A much larger repeatable market and scalable distribution are demonstrated.','Premature for an unvalidated niche prototype. Do not reshape the product around an unsupported market-size narrative.']],[.27,.35,.38]),
 H('A lean first team'),
 P('Founder: customer discovery, technical product direction, demonstrations and pricing. Contract engineer: shared tracking/provenance, release hardening and test automation under explicit deliverables. Fractional specialists: independent LPBF review, Windows/security acceptance, legal/IP and accounting. Buy a specialist review where needed rather than implying one person can certify every aspect.'),
 P('In the first four weeks, reserve roughly two days/week for customer discovery, two for technical hardening and one for pilot preparation/administration. During pilots, stagger starts and book delivery hours explicitly. The model pays external delivery labour separately from founder development/sales; adjust the staffing plan if those roles overlap.'),
 H('Size the opportunity from reachable accounts'),
 P('Build a source-linked account list, then measure the fraction with usable exports, enough review volume, budget and access permission. Reachable annual licence opportunity = qualified compatible sites × expected paid adoption × licence value. For illustration only, 200 qualified sites at 10% adoption and €6,000 gives €120,000 ARR; those site/adoption figures have not been verified. Do not present this arithmetic as global TAM.'),
 C('Next funding artifact: a 12-month monthly cash plan with actual hiring/payment dates, downside collections and minimum reserve. Seek outside capital only for a defined milestone, not to subsidize indefinitely unpriced support.'))
funding_page=pages.pop();pages.insert(next(i for i,p in enumerate(pages) if p['title']=='Risk register and response'),funding_page)
