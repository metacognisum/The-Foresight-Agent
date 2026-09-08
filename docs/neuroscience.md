# Neuroscience foundations for Foresight

Research note — 9 September 2026. The purpose is to constrain the design with
evidence, not to retrospectively label every software component a brain region.

## Central hypothesis

Predicting an action's evidence, the agent's subsequent explicit beliefs, and its
next decision may let a controller intervene before an unsupported conclusion
propagates. This is an engineering hypothesis. The cited neuroscience does not
demonstrate this particular computation in humans or establish its novelty in AI.

## 1. Forward models and sensory prediction error

**Evidence.** Tseng et al. (2007) investigated reaching adaptation and found support
for a role of sensory prediction error in cerebellum-dependent adaptation. The
distinction is between predicted and received sensory feedback, rather than merely
whether a task was successful.

**Engineering inference.** Record expected observations before execution. Compare
them with observations supplied by the executor. Keep tool failure, forecast error,
and task failure separate: a successful search can return evidence contradicting
the agent's hypothesis.

**Limit.** Motor adaptation does not establish that the same algorithm handles
language-based evidence or future beliefs. Our rule-based discrepancy handling is
not a cerebellar simulation.

Source: [Tseng et al., Sensory prediction errors drive cerebellum-dependent adaptation of reaching](https://pubmed.ncbi.nlm.nih.gov/17507504/).

## 2. Prospective hippocampal sequences

**Evidence.** Pfeiffer and Foster (2013) recorded rat hippocampal activity and found
brief sequences, before navigation, depicting paths biased toward remembered goals.
These findings support prospective representations relevant to navigation.

**Engineering inference.** Preview a short continuation: action, expected evidence,
resulting belief, subsequent decision. Judge where the continuation leads before
executing its first action.

**Limit.** Spatial trajectories do not demonstrate prediction of abstract future
beliefs. We should not equate an LLM-generated continuation with hippocampal replay.

Source: [Pfeiffer and Foster, Hippocampal place cell sequences depict future paths to remembered goals](https://pmc.ncbi.nlm.nih.gov/articles/PMC3990408/).

**Counterevidence to an overly broad story.** Preplay before novel experience has
been reported, but Silva, Feng and Foster (2015) found trajectory events required
previous experience in their experiments. Use the narrower claim that prospective
sequences related to learned environments exist; do not claim the brain accurately
simulates arbitrary unfamiliar futures.

Sources: [Dragoi and Tonegawa, 2011](https://www.nature.com/articles/nature09633);
[Silva et al., 2015](https://www.nature.com/articles/nn.4151).

## 3. Reality monitoring and source attribution

**Evidence.** Simons et al. (2006) used fMRI while healthy volunteers distinguished
previously perceived from imagined information, examining neural contributions to
source attribution.

**Engineering inference.** Predictions must never be silently promoted to observed
facts. Store provenance and let only trusted execution adapters add observations.
An imagined successful check cannot satisfy an actual completion requirement.

**Limit.** Reality monitoring is fallible and distributed. A software provenance
rule is an engineered invariant, not a model of a single brain region or proof
that an agent possesses awareness.

Source: [Simons et al., Discriminating imagined from perceived information engages brain areas implicated in schizophrenia](https://pubmed.ncbi.nlm.nih.gov/16797186/).

## 4. Metacognitive monitoring is distinct from task performance

**Evidence.** Fleming et al. (2010) linked individual differences in introspective
accuracy to brain structure. A later lesion study reported impaired perceptual
metacognitive accuracy with preserved task performance and memory metacognition,
supporting a domain-specific contribution of anterior prefrontal cortex.

**Engineering inference.** Measure task success separately from the ability to
predict success and recognize unsupported beliefs. A confident system can be wrong;
an accurate system can still be poorly calibrated. Evaluate by task and tool type.

**Limit.** These studies do not establish a universal confidence module. Structural
correlations alone are not causal evidence; the lesion findings are domain-limited.

Sources: [Fleming et al., 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC3173849/);
[Fleming et al., 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4163038/).

## 5. Task-state representations

**Evidence.** Schuck et al. (2016) decoded task-state information from human
orbitofrontal cortex using fMRI, supporting a cognitive map of task space that can
include information not immediately observable.

**Engineering inference.** Represent state using task-relevant requirements,
evidence, and unresolved claims, rather than an undifferentiated chat transcript.

**Limit.** The study does not specify our schema or show that structured software
state is a brain-equivalent cognitive map.

Source: [Schuck et al., Human Orbitofrontal Cortex Represents a Cognitive Map of State Space](https://pmc.ncbi.nlm.nih.gov/articles/PMC5044873/).

## 6. Allocating control has a cost

**Theory.** Shenhav, Botvinick and Cohen (2013) proposed the expected value of control
account: control allocation depends on prospective benefits and costs. This is a
theoretical synthesis, not proof that a specific scalar software objective is
biologically correct.

**Engineering inference.** Compare targeted checks with blanket verification.
Prediction should save mistakes at an acceptable execution and token cost. Always
checking everything is a baseline, not evidence of intelligent control.

Source: [The expected value of control](https://pmc.ncbi.nlm.nih.gov/articles/PMC3767969/).

## Prior work explicitly connecting neuroscience to metacognitive AI

[From internal models toward metacognitive AI (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8551129/)
already proposes a connection between internal models, mismatch-based selection,
and metacognition. Therefore “internal models plus metacognition” is not our novelty.
Nor does a neuroscience analogy supply evidence of software effectiveness.

## What we may honestly claim

Foresight is inspired by forward prediction, source monitoring, and metacognitive
control. Its proposed contribution is an explicit, testable controller over predicted
evidence, predicted beliefs and downstream decisions. Whether the combination is
novel needs a fuller literature review; whether it helps needs controlled experiments.

Do not claim consciousness, direct access to hidden model beliefs, biological
fidelity, human-like learning, or benchmark improvement from the current prototype.
